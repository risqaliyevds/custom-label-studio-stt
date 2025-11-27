# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a Label Studio ML Backend for audio analysis using Google's Gemini AI. It provides comprehensive audio analysis including transcription, speaker diarization, emotion detection, and multi-language support. The backend integrates with Label Studio for audio annotation workflows.

## Commands

### Development Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables (copy .env.example if available or use existing .env)
# Ensure GEMINI_API_KEY is set
```

### Running the Application
```bash
# Run enhanced API (recommended - full features)
source venv/bin/activate
python src/enhanced_api.py

# Run simple API (minimal implementation)
python src/simple_api.py

# Using Docker
docker-compose up --build
```

### Testing
```bash
# Run Python tests
python tests/test_enhanced.py
python tests/test_predict.py

# Run API integration tests
bash tests/test_api.sh

# Test health endpoint
curl http://localhost:9090/health
```

### Linting and Type Checking
```bash
# The project doesn't have explicit linting setup yet
# Consider adding: ruff, black, mypy for Python code quality
```

## Architecture

### Implementation Approaches

The project provides two implementations:

1. **Enhanced API** (`src/enhanced_api.py`):
   - Advanced speaker diarization with 0.1s precision timing
   - Multi-language support (Uzbek Latin, Russian Cyrillic, Arabic, English, Turkish)
   - Emotion detection (11 types: neutral, joy, sadness, anger, fear, surprise, disgust, contempt, confusion, disappointment, frustration)
   - Gender identification
   - Comprehensive summaries and key points extraction
   - Prometheus metrics integration
   - Structured JSON logging

2. **Simple API** (`src/simple_api.py`):
   - Basic transcription and language detection
   - Simple speaker identification
   - Summary generation
   - Single-file implementation for easy deployment
   - Minimal dependencies

### Request Flow

1. Label Studio sends POST request to `/predict` with audio file URLs
2. Backend downloads audio to `/tmp/audio_analysis/` temporary storage
3. Audio is processed using Google Gemini API with specific prompts for each analysis type
4. Results are formatted according to Label Studio's prediction format
5. Temporary files are automatically cleaned up after processing

### Key Components

- **FastAPI Application**: Async web framework handling API requests
- **Gemini Integration**: Uses `google.generativeai` for audio analysis
- **File Management**: Async file operations with automatic cleanup
- **Error Handling**: Comprehensive error handling with retries using tenacity
- **Monitoring**: Prometheus metrics for request tracking (enhanced version)

### Environment Configuration

Required environment variables:
- `GEMINI_API_KEY`: Google AI Studio API key (required)
- `GEMINI_MODEL`: Model name (default: "gemini-1.5-flash-8b")
- `API_HOST`: Server host (default: "0.0.0.0")
- `API_PORT`: Server port (default: 9090)
- `LOG_LEVEL`: Logging level (default: "INFO")

### Label Studio Integration

The backend follows Label Studio ML backend specification:
- `/setup` endpoint for initialization
- `/predict` endpoint for generating predictions
- Returns predictions in Label Studio's expected format with proper task IDs
- Supports both URL-based and direct file upload

### Docker Deployment

The project includes:
- Multi-stage Dockerfile with non-root user for security
- docker-compose.yml with complete service configuration
- Health checks and restart policies
- Volume mounting for logs persistence

## Important Notes

- The `scripts/start_api.sh` references a non-existent `main.py` - use `src/enhanced_api.py` instead
- Temporary audio files are stored in `/tmp/audio_analysis/` and cleaned up automatically
- The project uses async/await patterns throughout for better performance
- Error responses include detailed messages for debugging
- The enhanced API provides more detailed analysis but may have higher latency