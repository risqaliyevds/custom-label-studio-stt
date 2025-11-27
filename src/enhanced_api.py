#!/usr/bin/env python3
"""
Enhanced Label Studio ML Backend for Audio Analysis using Gemini API
With improved speaker diarization, language-specific transcription, and per-segment analysis
"""

import os
import json
import asyncio
import tempfile
import uuid
from typing import Dict, List, Any
from pathlib import Path

import uvicorn
from fastapi import FastAPI, HTTPException
from fastapi.middleware.cors import CORSMiddleware
import httpx
import google.generativeai as genai
from pydantic import BaseModel


# Configuration
GEMINI_API_KEY = os.getenv("GEMINI_API_KEY", "")
GEMINI_MODEL = os.getenv("GEMINI_MODEL", "gemini-2.0-flash")  # Read from .env, default to 2.0
LABEL_STUDIO_URL = os.getenv("LABEL_STUDIO_URL", "http://localhost:8080")
LABEL_STUDIO_API_KEY = os.getenv("LABEL_STUDIO_API_KEY", "")
PORT = int(os.getenv("PORT", "9090"))
HOST = os.getenv("HOST", "0.0.0.0")


# Initialize FastAPI
app = FastAPI(
    title="Enhanced Label Studio Audio ML Backend",
    description="Advanced audio analysis with speaker diarization and language-specific transcription",
    version="2.0.0"
)

# Add CORS
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


# Initialize Gemini
def init_gemini():
    """Initialize Gemini AI model"""
    if not GEMINI_API_KEY:
        raise ValueError("GEMINI_API_KEY environment variable is required")
    
    genai.configure(api_key=GEMINI_API_KEY)
    
    # Using Gemini model from environment configuration
    model_name = GEMINI_MODEL  # Gets model from .env file
    print(f"Using Gemini model: {model_name}")
    
    # Configure safety settings to be less restrictive
    safety_settings = [
        {"category": "HARM_CATEGORY_HARASSMENT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_HATE_SPEECH", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_SEXUALLY_EXPLICIT", "threshold": "BLOCK_NONE"},
        {"category": "HARM_CATEGORY_DANGEROUS_CONTENT", "threshold": "BLOCK_NONE"},
    ]
    
    model = genai.GenerativeModel(
        model_name,
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,  # Low temperature for consistent results
            max_output_tokens=16384,
            response_mime_type="application/json"
        ),
        safety_settings=safety_settings
    )
    return model


# Enhanced analysis prompt - English with robust requirements  
ENHANCED_ANALYSIS_PROMPT = """
You are an expert audio analyst. Perform a COMPREHENSIVE and PRECISE analysis of this audio file.

CRITICAL REQUIREMENTS - FOLLOW WITH EXTREME ACCURACY:

1. SPEAKER DIARIZATION (MUST BE PERFECT):
   - Identify EVERY unique speaker and assign consistent IDs: "Speaker 1", "Speaker 2", etc.
   - Track the SAME speaker throughout the ENTIRE audio - never mix speakers
   - Mark speaker changes with EXACT timestamps (precision to 0.1 seconds)
   - If uncertain about speaker identity, create a NEW speaker ID
   - Pay attention to: voice pitch, tone, accent, speaking style, breathing patterns

2. TIMING PRECISION (CRITICAL):
   - Provide EXACT start_time and end_time in seconds (e.g., 0.0, 3.7, 15.2)
   - NO gaps between segments - continuous coverage required
   - NO overlapping segments allowed
   - Minimum segment duration: 0.5 seconds
   - Maximum segment duration: 30 seconds (split longer speech appropriately)
   - Total coverage must equal audio duration

3. TRANSCRIPTION ACCURACY (WORD-PERFECT):
   - Transcribe EXACTLY what is said, including:
     * Hesitations (um, uh, er)
     * Repetitions and false starts
     * Incomplete words or sentences
   - Use CORRECT script for each language:
     * Uzbek: Latin script with proper apostrophes (o', g', ng) - e.g., "O'zbekiston", "yaxshi", "to'g'ri"
     * Russian: Cyrillic script - e.g., "правильно", "хорошо"
     * Arabic: Arabic script - e.g., "العربية", "مرحبا"
     * English: Latin script
     * Turkish: Latin with Turkish characters (ğ, ş, ı, ö, ü, ç)
   - Preserve code-switching and mixed languages

4. LANGUAGE DETECTION (PER SEGMENT):
   - Identify the PRIMARY language of each segment
   - Use codes: "Uzbek", "Russian", "Arabic", "English", "Turkish", "Other"
   - For mixed segments, choose the DOMINANT language (>60% of words)
   - Be consistent - if speaker uses same language, keep it consistent

5. GENDER IDENTIFICATION (ACCURATE):
   - Analyze voice characteristics:
     * Fundamental frequency: Male (85-180 Hz), Female (165-255 Hz)
     * Vocal tract length and formants
     * Speaking patterns and intonation
   - Options: "Male", "Female", "Unknown"
   - Use "Unknown" ONLY when truly ambiguous or child voice

6. EMOTION DETECTION (NUANCED):
   - Detect PRIMARY emotion based on:
     * Pitch variations and prosody
     * Speaking rate and rhythm
     * Volume and intensity
     * Voice quality (breathy, tense, creaky)
   - Emotions: "Neutral", "Happy", "Sad", "Angry", "Surprised", "Fearful", 
              "Disgusted", "Excited", "Calm", "Frustrated", "Confident"
   - Choose most prominent emotion, not just default to "Neutral"

7. SUMMARY GENERATION (DETAILED IN UZBEK LATIN):
   - Write in Uzbek Latin script ONLY
   - Include:
     * Asosiy mavzular (main topics discussed)
     * Har bir spiker nimani aytdi (what each speaker said)
     * Muhim nuqtalar va xulosalar (key points and conclusions)
     * Suhbat ohangi va kayfiyati (conversation tone and mood)
     * Qaror yoki kelishuvlar (decisions or agreements)
   - Length: 4-8 sentences with substantive content

STRICT JSON OUTPUT FORMAT:
{
    "segments": [
        {
            "speaker_id": "Speaker 1",
            "start_time": 0.0,
            "end_time": 5.3,
            "text": "Exact transcription in appropriate script",
            "language": "Uzbek",
            "gender": "Male",
            "emotion": "Neutral",
            "confidence": 0.95
        }
    ],
    "speakers": [
        {
            "id": "Speaker 1",
            "total_speaking_time": 45.3,
            "gender": "Male",
            "primary_language": "Uzbek",
            "segments_count": 12
        }
    ],
    "summary_uzbek": "Detailed summary in Uzbek Latin script...",
    "total_duration": 120.5,
    "languages_detected": ["Uzbek", "Russian"],
    "dominant_emotion": "Neutral"
}

QUALITY CONTROL CHECKLIST:
✓ All speakers correctly identified and tracked
✓ Timestamps are precise and continuous
✓ Transcription is word-perfect in correct scripts
✓ Languages accurately detected
✓ Gender identification is reliable
✓ Emotions are nuanced, not just "Neutral"
✓ Summary is comprehensive and in Uzbek Latin

Return ONLY valid JSON. No explanations or additional text.
"""


async def get_access_token():
    """Get access token from refresh token if needed"""
    global LABEL_STUDIO_API_KEY
    
    if not LABEL_STUDIO_API_KEY:
        return None
    
    # If it's a JWT refresh token, try to get an access token
    if LABEL_STUDIO_API_KEY.startswith("eyJ"):
        try:
            async with httpx.AsyncClient() as client:
                response = await client.post(
                    f"{LABEL_STUDIO_URL}/api/token/refresh/",
                    json={"refresh": LABEL_STUDIO_API_KEY},
                    timeout=10.0
                )
                if response.status_code == 200:
                    data = response.json()
                    access_token = data.get("access")
                    if access_token:
                        print(f"Got access token from refresh token")
                        return access_token
        except Exception as e:
            print(f"Could not refresh token: {e}")
    
    # Return original token if refresh fails or it's not a JWT
    return LABEL_STUDIO_API_KEY


async def download_audio(url: str) -> str:
    """Download audio file from URL or handle local file"""
    try:
        # First check if it's just a filename (like test.mp3)
        if not url.startswith(("http://", "https://", "file://", "/")):
            # It's likely just a filename, check in the current directory
            local_path = f"/mnt/mata/labelStudio/{url}"
            if os.path.exists(local_path):
                print(f"Found local file at: {local_path}")
                return local_path
        
        # Check if it's a local file reference
        if url.startswith("/") and not url.startswith(("http://", "https://")):
            # Try to find local file
            if url == "/test.mp3":
                local_path = "/mnt/mata/labelStudio/test.mp3"
                if os.path.exists(local_path):
                    print(f"Found test file at: {local_path}")
                    return local_path
            local_path = f"/mnt/mata/labelStudio{url}"
            if os.path.exists(local_path):
                print(f"Found local file at: {local_path}")
                return local_path
            # Also check without the leading slash
            local_path = f"/mnt/mata/labelStudio/{url.lstrip('/')}"
            if os.path.exists(local_path):
                print(f"Found local file at: {local_path}")
                return local_path
        
        # Check if it's file:// URL
        if url.startswith("file://"):
            local_path = url[7:]  # Remove 'file://' prefix
            if os.path.exists(local_path):
                print(f"Found file:// at: {local_path}")
                return local_path
        
        # Create temporary file for download
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_path = temp_file.name
        temp_file.close()
        
        # Construct full URL if needed
        if not url.startswith(("http://", "https://")):
            if url.startswith("/"):
                url = f"{LABEL_STUDIO_URL}{url}"
            else:
                url = f"{LABEL_STUDIO_URL}/data/{url}"
        
        # Download file
        async with httpx.AsyncClient() as client:
            headers = {}
            
            # Get access token (handles refresh if needed)
            token = await get_access_token()
            if token:
                # Use Bearer for JWT tokens, Token for legacy tokens
                if token.startswith("eyJ"):
                    headers["Authorization"] = f"Bearer {token}"
                    print(f"Using Bearer auth with token: {token[:20]}...")
                else:
                    headers["Authorization"] = f"Token {token}"
                    print(f"Using Token auth with token: {token[:20]}...")
            
            response = await client.get(url, headers=headers, timeout=30.0)
            response.raise_for_status()
            
            # Save to temp file
            with open(temp_path, "wb") as f:
                f.write(response.content)
        
        return temp_path
        
    except Exception as e:
        print(f"Error downloading audio: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Failed to download audio: {str(e)}")


def get_fallback_response() -> Dict[str, Any]:
    """Return a fallback response when Gemini blocks content due to safety reasons"""
    return {
        "segments": [
            {
                "start_time": 0.0,
                "end_time": 10.0,
                "speaker_id": "Speaker_1",
                "text": "[Content could not be analyzed due to safety filters]",
                "language": "unknown",
                "gender": "unknown",
                "emotion": "neutral"
            }
        ],
        "summary_uzbek": "Audio tahlili xavfsizlik filtrlari tufayli bajarilmadi. Iltimos, audio faylni tekshiring va qayta urinib ko'ring.",
        "languages_detected": ["unknown"],
        "total_speakers": 1,
        "emotions_detected": ["neutral"],
        "named_entities": []
    }


def analyze_audio_with_gemini(audio_path: str) -> Dict[str, Any]:
    """Analyze audio file using Gemini with enhanced prompt and retry logic"""
    max_retries = 3
    retry_count = 0
    
    while retry_count < max_retries:
        try:
            model = init_gemini()
            
            # Upload audio file
            audio_file = genai.upload_file(audio_path, mime_type="audio/mpeg")
            
            # Generate analysis with enhanced prompt
            response = model.generate_content([
                ENHANCED_ANALYSIS_PROMPT,
                audio_file
            ])
            
            # Check if response was blocked
            if not response.parts:
                # Check finish reason
                if response.candidates and response.candidates[0].finish_reason:
                    finish_reason = response.candidates[0].finish_reason
                    print(f"Response blocked with finish_reason: {finish_reason}")
                    
                    # If it's a safety block, retry with modified prompt
                    if finish_reason == 2:  # SAFETY
                        retry_count += 1
                        if retry_count < max_retries:
                            print(f"Retrying with simpler prompt (attempt {retry_count}/{max_retries})...")
                            # Try with a simpler prompt
                            simple_prompt = """Analyze this audio and provide a JSON response with:
- segments: array of speaker segments with start_time, end_time, speaker_id, text, language
- summary_uzbek: brief summary in Uzbek
- languages_detected: array of detected languages"""
                            response = model.generate_content([simple_prompt, audio_file])
                            if response.parts:
                                text = response.text.strip()
                                # Clean up response if needed
                                if text.startswith("```json"):
                                    text = text[7:]
                                if text.endswith("```"):
                                    text = text[:-3]
                                result = json.loads(text)
                                return result
                            else:
                                # Still blocked, return fallback
                                print(f"Still blocked after retry {retry_count}")
                                return get_fallback_response()
                        else:
                            # Max retries reached
                            return get_fallback_response()
                    else:
                        # Not a safety block, return fallback
                        print(f"Response blocked with non-safety reason: {finish_reason}")
                        return get_fallback_response()
                else:
                    # No candidates, return fallback
                    print("No response candidates generated")
                    return get_fallback_response()
            
            # We have a valid response
            text = response.text.strip()
            # Clean up response if needed
            if text.startswith("```json"):
                text = text[7:]
            if text.endswith("```"):
                text = text[:-3]
            
            result = json.loads(text)
            return result
            
        except json.JSONDecodeError as e:
            print(f"JSON parsing error (attempt {retry_count + 1}/{max_retries}): {str(e)}")
            retry_count += 1
            if retry_count >= max_retries:
                # Return a default structure on final failure
                return {
                    "segments": [
                        {
                            "speaker_id": "Speaker 1",
                            "start_time": 0,
                            "end_time": 1,
                            "text": "Audio tahlil qilishda xatolik yuz berdi",
                            "language": "Uzbek",
                            "gender": "Unknown",
                            "emotion": "Neutral",
                            "confidence": 0.0
                        }
                    ],
                    "speakers": [],
                    "summary_uzbek": "Audio tahlil qilishda xatolik yuz berdi",
                    "total_duration": 0,
                    "languages_detected": [],
                    "dominant_emotion": "Neutral"
                }
            continue
            
        except Exception as e:
            print(f"Gemini analysis error (attempt {retry_count + 1}/{max_retries}): {str(e)}")
            retry_count += 1
            if retry_count >= max_retries:
                # Return a fallback response
                return {
                    "segments": [
                        {
                            "speaker_id": "Speaker 1",
                            "start_time": 0,
                            "end_time": 1,
                            "text": "Audio tahlilida xatolik",
                            "language": "Uzbek",
                            "gender": "Unknown",
                            "emotion": "Neutral",
                            "confidence": 0.0
                        }
                    ],
                    "speakers": [],
                    "summary_uzbek": "Audio tahlilida xatolik",
                    "total_duration": 0,
                    "languages_detected": [],
                    "dominant_emotion": "Neutral"
                }
            continue
    
    # If all retries failed
    raise HTTPException(status_code=500, detail="Failed to analyze audio after multiple attempts")


def format_enhanced_predictions(analysis: Dict[str, Any], task_id: int) -> Dict[str, Any]:
    """Convert enhanced Gemini analysis to Label Studio prediction format"""
    
    predictions = []
    
    # Process each segment for speaker diarization with all attributes
    if analysis.get("segments"):
        for segment in analysis["segments"]:
            # Generate unique ID for this segment
            segment_id = str(uuid.uuid4())[:8]
            
            # Get segment details
            start_time = segment.get("start_time", 0)
            end_time = segment.get("end_time", 0)
            
            # 1. Speaker label (main region on audio)
            predictions.append({
                "id": segment_id,
                "value": {
                    "start": start_time,
                    "end": end_time,
                    "labels": [segment.get("speaker_id", "Speaker 1")],
                    "channel": 0
                },
                "from_name": "speaker_labels",
                "to_name": "audio",
                "type": "labels",
                "origin": "prediction"
            })
            
            # 2. Language detection (same region ID)
            if segment.get("language"):
                predictions.append({
                    "id": segment_id,
                    "value": {
                        "start": start_time,
                        "end": end_time,
                        "choices": [segment["language"]],
                        "channel": 0
                    },
                    "from_name": "language",
                    "to_name": "audio",
                    "type": "choices",
                    "origin": "prediction"
                })
            
            # 3. Gender identification (same region ID)
            if segment.get("gender"):
                predictions.append({
                    "id": segment_id,
                    "value": {
                        "start": start_time,
                        "end": end_time,
                        "choices": [segment["gender"]],
                        "channel": 0
                    },
                    "from_name": "gender",
                    "to_name": "audio",
                    "type": "choices",
                    "origin": "prediction"
                })
            
            # 4. Emotion analysis (same region ID)
            if segment.get("emotion"):
                predictions.append({
                    "id": segment_id,
                    "value": {
                        "start": start_time,
                        "end": end_time,
                        "choices": [segment["emotion"]],
                        "channel": 0
                    },
                    "from_name": "emotion",
                    "to_name": "audio",
                    "type": "choices",
                    "origin": "prediction"
                })
            
            # 5. Transcription (same region ID)
            if segment.get("text"):
                predictions.append({
                    "id": segment_id,
                    "value": {
                        "start": start_time,
                        "end": end_time,
                        "text": [segment["text"]],
                        "channel": 0
                    },
                    "from_name": "transcription",
                    "to_name": "audio",
                    "type": "textarea",
                    "origin": "prediction"
                })
    
    # 6. Summary in Uzbek
    if analysis.get("summary_uzbek"):
        predictions.append({
            "value": {
                "text": [analysis["summary_uzbek"]]
            },
            "from_name": "summary",
            "to_name": "audio",
            "type": "textarea",
            "origin": "prediction"
        })
    
    return {
        "result": predictions,
        "score": 0.95,
        "model_version": "gemini-1.5-flash-enhanced"
    }


# API Endpoints

@app.get("/")
async def root():
    """ML Backend info"""
    return {
        "model_class": "EnhancedGeminiAudioMLBackend",
        "status": "UP",
        "version": "2.0.0",
        "features": [
            "speaker_diarization",
            "language_specific_transcription",
            "per_segment_analysis",
            "uzbek_summaries"
        ]
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}


@app.post("/setup")
async def setup(request: Dict[str, Any]):
    """Setup endpoint for Label Studio"""
    return {
        "model_version": "gemini-1.5-flash-enhanced",
        "status": "ready"
    }


@app.post("/predict")
async def predict(request: Dict[str, Any]):
    """
    Generate enhanced predictions for Label Studio tasks
    """
    
    # Validate request
    if not request or "tasks" not in request:
        raise HTTPException(status_code=422, detail="Request must contain 'tasks'")
    
    tasks = request.get("tasks", [])
    if not tasks:
        raise HTTPException(status_code=422, detail="At least one task required")
    
    results = []
    
    for task in tasks:
        try:
            # Extract audio path
            task_id = task.get("id", 1)
            audio_url = task.get("data", {}).get("audio")
            
            if not audio_url:
                print(f"No audio URL in task {task_id}")
                continue
            
            print(f"Processing task {task_id}: {audio_url}")
            
            # Download audio
            audio_path = await download_audio(audio_url)
            
            try:
                # Analyze with enhanced Gemini prompt
                analysis = analyze_audio_with_gemini(audio_path)
                
                # Format for Label Studio
                prediction = format_enhanced_predictions(analysis, task_id)
                results.append(prediction)
                
                print(f"Task {task_id} processed successfully")
                print(f"Found {len(analysis.get('segments', []))} segments")
                print(f"Languages: {analysis.get('languages_detected', [])}")
                
            finally:
                # Clean up temp file
                if os.path.exists(audio_path) and audio_path.startswith("/tmp"):
                    os.unlink(audio_path)
            
        except Exception as e:
            print(f"Error processing task {task.get('id')}: {str(e)}")
            # Add empty prediction on error
            results.append({
                "result": [],
                "score": 0.0,
                "model_version": "gemini-1.5-flash-enhanced"
            })
    
    # Return in Label Studio format
    return {"results": results}


@app.post("/train")
async def train(request: Dict[str, Any]):
    """Training endpoint (not implemented)"""
    return {"status": "Training not supported"}


if __name__ == "__main__":
    # Check for API key
    if not GEMINI_API_KEY:
        print("ERROR: GEMINI_API_KEY environment variable is required")
        print("Set it with: export GEMINI_API_KEY=your_api_key_here")
        exit(1)
    
    print(f"Starting Enhanced Label Studio ML Backend on {HOST}:{PORT}")
    print(f"Gemini Model: {GEMINI_MODEL}")
    print(f"Gemini API Key: {GEMINI_API_KEY[:20]}...")
    print(f"Features: Speaker diarization, Language-specific transcription, Per-segment analysis")
    
    uvicorn.run(app, host=HOST, port=PORT)