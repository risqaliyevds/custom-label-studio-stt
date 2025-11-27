#!/usr/bin/env python3
"""
Simplified Label Studio ML Backend for Audio Analysis using Gemini API
"""

import os
import json
import asyncio
import tempfile
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
LABEL_STUDIO_URL = os.getenv("LABEL_STUDIO_URL", "http://localhost:8080")
LABEL_STUDIO_API_KEY = os.getenv("LABEL_STUDIO_API_KEY", "")
PORT = int(os.getenv("PORT", "9090"))
HOST = os.getenv("HOST", "0.0.0.0")


# Initialize FastAPI
app = FastAPI(
    title="Label Studio Audio ML Backend",
    description="Audio analysis predictions using Gemini AI",
    version="1.0.0"
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
    
    model = genai.GenerativeModel(
        "gemini-1.5-flash",
        generation_config=genai.types.GenerationConfig(
            temperature=0.1,
            max_output_tokens=8192,
        )
    )
    return model


# Analysis prompt
ANALYSIS_PROMPT = """
Analyze this audio file and provide a comprehensive analysis in JSON format:

{
    "transcription": [
        {
            "text": "transcribed text",
            "start_time": 0.0,
            "end_time": 5.0,
            "speaker": "Speaker 1"
        }
    ],
    "language": "detected language",
    "speakers": [
        {
            "id": "Speaker 1",
            "gender": "male/female/unknown",
            "emotion": "neutral/happy/sad/angry"
        }
    ],
    "summary": "brief summary of content",
    "duration": 120.5
}

Provide ONLY valid JSON in your response, no additional text.
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
        # Check if it's a local file reference
        if url.startswith("/") and not url.startswith(("http://", "https://")):
            # Try to find local file
            local_path = f"/mnt/mata/labelStudio{url}"
            if os.path.exists(local_path):
                return local_path
            # Also check without the leading slash
            local_path = f"/mnt/mata/labelStudio/{url.lstrip('/')}"
            if os.path.exists(local_path):
                return local_path
        
        # Check if it's file:// URL
        if url.startswith("file://"):
            local_path = url[7:]  # Remove 'file://' prefix
            if os.path.exists(local_path):
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


def analyze_audio_with_gemini(audio_path: str) -> Dict[str, Any]:
    """Analyze audio file using Gemini"""
    try:
        model = init_gemini()
        
        # Upload audio file
        audio_file = genai.upload_file(audio_path, mime_type="audio/mpeg")
        
        # Generate analysis
        response = model.generate_content([
            ANALYSIS_PROMPT,
            audio_file
        ])
        
        # Parse JSON response
        text = response.text.strip()
        # Clean up response if needed
        if text.startswith("```json"):
            text = text[7:]
        if text.endswith("```"):
            text = text[:-3]
        
        result = json.loads(text)
        return result
        
    except json.JSONDecodeError as e:
        print(f"JSON parsing error: {str(e)}")
        # Return a default structure
        return {
            "transcription": [{"text": "Audio processed but could not parse response", "start_time": 0, "end_time": 1}],
            "language": "unknown",
            "speakers": [],
            "summary": "Analysis failed",
            "duration": 0
        }
    except Exception as e:
        print(f"Gemini analysis error: {str(e)}")
        raise HTTPException(status_code=500, detail=f"Gemini analysis failed: {str(e)}")


def format_label_studio_predictions(analysis: Dict[str, Any], task_id: int) -> Dict[str, Any]:
    """Convert Gemini analysis to Label Studio prediction format"""
    
    predictions = []
    
    # Add transcription
    if analysis.get("transcription"):
        for segment in analysis["transcription"]:
            predictions.append({
                "value": {
                    "start": segment.get("start_time", 0),
                    "end": segment.get("end_time", 0),
                    "text": [segment.get("text", "")],
                    "channel": 0
                },
                "from_name": "transcription",
                "to_name": "audio",
                "type": "textarea",
                "origin": "prediction"
            })
    
    # Add language detection
    if analysis.get("language"):
        predictions.append({
            "value": {
                "choices": [analysis["language"]]
            },
            "from_name": "language",
            "to_name": "audio",
            "type": "choices",
            "origin": "prediction"
        })
    
    # Add speaker labels
    if analysis.get("speakers"):
        for speaker in analysis["speakers"]:
            if speaker.get("gender"):
                predictions.append({
                    "value": {
                        "choices": [speaker["gender"]]
                    },
                    "from_name": "gender",
                    "to_name": "audio",
                    "type": "choices",
                    "origin": "prediction"
                })
            
            if speaker.get("emotion"):
                predictions.append({
                    "value": {
                        "choices": [speaker["emotion"]]
                    },
                    "from_name": "emotion",
                    "to_name": "audio",
                    "type": "choices",
                    "origin": "prediction"
                })
    
    # Add summary
    if analysis.get("summary"):
        predictions.append({
            "value": {
                "text": [analysis["summary"]]
            },
            "from_name": "summary",
            "to_name": "audio",
            "type": "textarea",
            "origin": "prediction"
        })
    
    return {
        "result": predictions,
        "score": 0.95,
        "model_version": "gemini-1.5-flash"
    }


# API Endpoints

@app.get("/")
async def root():
    """ML Backend info"""
    return {
        "model_class": "GeminiAudioMLBackend",
        "status": "UP",
        "version": "1.0.0"
    }


@app.get("/health")
async def health():
    """Health check"""
    return {"status": "healthy"}


@app.post("/setup")
async def setup(request: Dict[str, Any]):
    """Setup endpoint for Label Studio"""
    return {
        "model_version": "gemini-1.5-flash",
        "status": "ready"
    }


@app.post("/predict")
async def predict(request: Dict[str, Any]):
    """
    Generate predictions for Label Studio tasks
    
    Expected format:
    {
        "tasks": [
            {
                "id": 1,
                "data": {
                    "audio": "/path/to/audio.mp3"
                }
            }
        ]
    }
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
                # Analyze with Gemini
                analysis = analyze_audio_with_gemini(audio_path)
                
                # Format for Label Studio
                prediction = format_label_studio_predictions(analysis, task_id)
                results.append(prediction)
                
            finally:
                # Clean up temp file
                if os.path.exists(audio_path):
                    os.unlink(audio_path)
            
        except Exception as e:
            print(f"Error processing task {task.get('id')}: {str(e)}")
            # Add empty prediction on error
            results.append({
                "result": [],
                "score": 0.0,
                "model_version": "gemini-1.5-flash"
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
    
    print(f"Starting Label Studio ML Backend on {HOST}:{PORT}")
    print(f"Gemini API Key: {GEMINI_API_KEY[:20]}...")
    
    uvicorn.run(app, host=HOST, port=PORT)