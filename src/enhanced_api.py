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
    import re
    import glob
    import urllib.parse

    print(f"[download_audio] Processing URL: {url}")

    try:
        # Label Studio media storage location
        LABEL_STUDIO_MEDIA_ROOT = os.path.expanduser("~/.local/share/label-studio/media")

        # Handle blob URLs - these can't be downloaded server-side
        if url.startswith("blob:"):
            raise HTTPException(
                status_code=400,
                detail="Blob URLs cannot be processed server-side. Please use a direct file URL."
            )

        # Strip http://localhost:PORT prefix if present - convert to relative path
        url = re.sub(r'^https?://[^/]+', '', url)
        print(f"[download_audio] Normalized URL: {url}")

        # First check if it's an absolute path that already exists
        if url.startswith("/") and os.path.exists(url):
            print(f"[download_audio] Found absolute path: {url}")
            return url

        # Check for Label Studio data URLs - map to local filesystem
        # Formats: /data/upload/{project_id}/{filename}, /data/local-files/?d=path

        # Pattern 1: /data/upload/{project_id}/{filename}
        data_upload_match = re.search(r'/data/upload/(\d+)/(.+?)(?:\?|$)', url)
        if data_upload_match:
            project_id = data_upload_match.group(1)
            filename = urllib.parse.unquote(data_upload_match.group(2))
            local_path = os.path.join(LABEL_STUDIO_MEDIA_ROOT, "upload", project_id, filename)
            print(f"[download_audio] Trying upload path: {local_path}")
            if os.path.exists(local_path):
                print(f"[download_audio] Found Label Studio media file: {local_path}")
                return local_path
            # Try to find by partial filename match
            search_pattern = os.path.join(LABEL_STUDIO_MEDIA_ROOT, "upload", project_id, f"*{filename.split('/')[-1]}*")
            matches = glob.glob(search_pattern)
            if matches:
                print(f"[download_audio] Found by pattern match: {matches[0]}")
                return matches[0]

        # Pattern 2: /data/local-files/?d=path
        local_files_match = re.search(r'/data/local-files/\?d=(.+?)(?:&|$)', url)
        if local_files_match:
            file_path = urllib.parse.unquote(local_files_match.group(1))
            print(f"[download_audio] Trying local-files path: {file_path}")
            if os.path.exists(file_path):
                return file_path

        # Pattern 3: Extract filename and search in all upload directories
        filename_match = re.search(r'([^/]+\.(?:mp3|wav|ogg|flac|m4a))(?:\?|$)', url, re.IGNORECASE)
        if filename_match:
            filename = urllib.parse.unquote(filename_match.group(1))
            print(f"[download_audio] Searching for filename: {filename}")
            # Search in all project upload directories
            for project_dir in glob.glob(os.path.join(LABEL_STUDIO_MEDIA_ROOT, "upload", "*")):
                search_path = os.path.join(project_dir, f"*{filename}*")
                matches = glob.glob(search_path)
                if matches:
                    print(f"[download_audio] Found file by name search: {matches[0]}")
                    return matches[0]
                # Also try exact match
                exact_path = os.path.join(project_dir, filename)
                if os.path.exists(exact_path):
                    print(f"[download_audio] Found exact match: {exact_path}")
                    return exact_path

        # Check if it's just a filename (like test.mp3)
        if not url.startswith(("http://", "https://", "file://", "/")):
            local_path = f"/mnt/mata/labelStudio/{url}"
            if os.path.exists(local_path):
                print(f"[download_audio] Found local file at: {local_path}")
                return local_path

        # Check if it's a local file reference starting with /
        if url.startswith("/") and not url.startswith(("http://", "https://")):
            # Try various path combinations
            paths_to_try = [
                url,
                f"/mnt/mata/labelStudio{url}",
                f"/mnt/mata/labelStudio/{url.lstrip('/')}",
            ]
            for path in paths_to_try:
                if os.path.exists(path):
                    print(f"[download_audio] Found local file at: {path}")
                    return path

        # Check if it's file:// URL
        if url.startswith("file://"):
            local_path = url[7:]  # Remove 'file://' prefix
            if os.path.exists(local_path):
                print(f"[download_audio] Found file:// at: {local_path}")
                return local_path

        # Last resort: Try to download from URL
        print(f"[download_audio] Attempting HTTP download for: {url}")

        # Create temporary file for download
        temp_file = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3")
        temp_path = temp_file.name
        temp_file.close()

        # Construct full URL if needed
        download_url = url
        if not url.startswith(("http://", "https://")):
            if url.startswith("/"):
                download_url = f"{LABEL_STUDIO_URL}{url}"
            else:
                download_url = f"{LABEL_STUDIO_URL}/data/{url}"

        print(f"[download_audio] Download URL: {download_url}")

        # Download file with retries
        async with httpx.AsyncClient(timeout=60.0) as client:
            headers = {}

            # Get access token (handles refresh if needed)
            token = await get_access_token()
            if token:
                if token.startswith("eyJ"):
                    headers["Authorization"] = f"Bearer {token}"
                else:
                    headers["Authorization"] = f"Token {token}"

            try:
                response = await client.get(download_url, headers=headers, follow_redirects=True)
                response.raise_for_status()

                with open(temp_path, "wb") as f:
                    f.write(response.content)

                print(f"[download_audio] Downloaded to: {temp_path}")
                return temp_path

            except httpx.HTTPStatusError as e:
                print(f"[download_audio] HTTP error {e.response.status_code}: {e}")
                os.unlink(temp_path)
                raise
            except Exception as e:
                print(f"[download_audio] Download error: {e}")
                os.unlink(temp_path)
                raise

    except HTTPException:
        raise
    except Exception as e:
        print(f"[download_audio] Error: {str(e)}")
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


# Pydantic models for segment transcription
class SegmentTranscribeRequest(BaseModel):
    audio_url: str
    start_time: float
    end_time: float
    task_id: int = 0
    project_id: int = 0


class SegmentTranscribeResponse(BaseModel):
    transcription: str
    language: str
    gender: str
    emotion: str
    confidence: float


SEGMENT_TRANSCRIBE_PROMPT = """
Analyze this audio segment and provide a detailed transcription.

REQUIREMENTS:
1. Transcribe EXACTLY what is said, word for word
2. Use the CORRECT script for the language:
   - Uzbek: Latin script with apostrophes (o', g', ng) - e.g., "O'zbekiston", "yaxshi"
   - Russian: Cyrillic script - e.g., "привет", "хорошо"
   - English: Latin script
   - Arabic: Arabic script
   - Turkish: Latin with Turkish characters (ğ, ş, ı, ö, ü, ç)
3. Include hesitations (um, uh, er) and repetitions
4. Detect the primary language
5. Identify speaker gender (Male/Female/Unknown)
6. Detect emotion (Neutral/Happy/Sad/Angry/Surprised/Fearful/Excited/Calm/Frustrated)

Return ONLY valid JSON in this format:
{
    "transcription": "Exact transcription text in appropriate script",
    "language": "Uzbek",
    "gender": "Male",
    "emotion": "Neutral",
    "confidence": 0.95
}
"""


async def extract_audio_segment(audio_path: str, start_time: float, end_time: float) -> str:
    """Extract a segment from audio file using ffmpeg"""
    import subprocess

    # Create temp file for segment
    segment_path = tempfile.NamedTemporaryFile(delete=False, suffix=".mp3").name

    duration = end_time - start_time

    # Use ffmpeg to extract segment
    cmd = [
        "ffmpeg", "-y",
        "-i", audio_path,
        "-ss", str(start_time),
        "-t", str(duration),
        "-acodec", "libmp3lame",
        "-ar", "16000",
        "-ac", "1",
        segment_path
    ]

    try:
        process = subprocess.run(
            cmd,
            capture_output=True,
            timeout=30
        )
        if process.returncode != 0:
            print(f"FFmpeg error: {process.stderr.decode()}")
            raise Exception(f"FFmpeg failed: {process.stderr.decode()}")

        return segment_path
    except subprocess.TimeoutExpired:
        raise Exception("FFmpeg timeout")
    except Exception as e:
        if os.path.exists(segment_path):
            os.unlink(segment_path)
        raise e


def transcribe_segment_with_gemini(audio_path: str) -> Dict[str, Any]:
    """Transcribe a single audio segment using Gemini"""
    try:
        model = init_gemini()

        # Upload audio file
        audio_file = genai.upload_file(audio_path, mime_type="audio/mpeg")

        # Generate transcription
        response = model.generate_content([
            SEGMENT_TRANSCRIBE_PROMPT,
            audio_file
        ])

        if not response.parts:
            return {
                "transcription": "[Could not transcribe]",
                "language": "Unknown",
                "gender": "Unknown",
                "emotion": "Neutral",
                "confidence": 0.0
            }

        text = response.text.strip()
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]

        result = json.loads(text)
        return result

    except json.JSONDecodeError as e:
        print(f"JSON parsing error in segment transcription: {e}")
        return {
            "transcription": "[Transcription error]",
            "language": "Unknown",
            "gender": "Unknown",
            "emotion": "Neutral",
            "confidence": 0.0
        }
    except Exception as e:
        print(f"Segment transcription error: {e}")
        return {
            "transcription": f"[Error: {str(e)}]",
            "language": "Unknown",
            "gender": "Unknown",
            "emotion": "Neutral",
            "confidence": 0.0
        }


@app.post("/transcribe-segment", response_model=SegmentTranscribeResponse)
async def transcribe_segment(request: SegmentTranscribeRequest):
    """
    Transcribe a specific audio segment using Gemini.
    Used for on-demand transcription when user selects a region.
    """
    print(f"Transcribe segment request: {request.audio_url} [{request.start_time:.2f} - {request.end_time:.2f}]")

    audio_path = None
    segment_path = None

    try:
        # Download the full audio
        audio_path = await download_audio(request.audio_url)

        # Extract the segment
        segment_path = await extract_audio_segment(
            audio_path,
            request.start_time,
            request.end_time
        )

        # Transcribe with Gemini
        result = transcribe_segment_with_gemini(segment_path)

        print(f"Transcription result: {result.get('transcription', '')[:100]}...")

        return SegmentTranscribeResponse(
            transcription=result.get("transcription", ""),
            language=result.get("language", "Unknown"),
            gender=result.get("gender", "Unknown"),
            emotion=result.get("emotion", "Neutral"),
            confidence=result.get("confidence", 0.0)
        )

    except Exception as e:
        print(f"Error in transcribe_segment: {e}")
        raise HTTPException(status_code=500, detail=str(e))

    finally:
        # Cleanup temp files
        if audio_path and os.path.exists(audio_path) and audio_path.startswith("/tmp"):
            os.unlink(audio_path)
        if segment_path and os.path.exists(segment_path):
            os.unlink(segment_path)


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