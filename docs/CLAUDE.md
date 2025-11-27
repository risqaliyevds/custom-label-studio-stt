# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Label Studio Audio Analysis ML Backend - A FastAPI-based machine learning backend for Label Studio that provides comprehensive audio analysis using Google's Gemini AI.

**Two Implementations:**
1. **Full Version** (`main.py` + `app/`) - Complete implementation with monitoring, health checks, and enterprise features
2. **Simplified Version** (`simple_api.py`) - Minimal, single-file implementation focused on core prediction functionality

## Common Development Commands

### Environment Setup
```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Set up environment variables
cp env.example .env
# Edit .env and set GEMINI_API_KEY
```

### Running the Application

**Simplified Version (Recommended for testing):**
```bash
# Quick start with minimal setup
./run_simple.sh

# Or directly
python simple_api.py
```

**Full Version:**
```bash
# Using startup script
./start_api.sh

# Direct Python execution with arguments
python main.py --host 0.0.0.0 --port 9090 --reload

# Using Docker
docker compose up -d
docker compose logs -f labelstudio-audio-api
```

### API Testing
```bash
# Check API health
curl http://localhost:9090/health

# View metrics
curl http://localhost:9090/metrics

# API documentation
# Visit http://localhost:9090/docs in browser
```

## Architecture Overview

### Core Components

**Entry Points:**
- `main.py` - CLI entry point with argument parsing and server startup
- `app/main.py` - FastAPI application with endpoint definitions and middleware

**Service Layer (`app/services/`):**
- `prediction_engine.py` - Orchestrates the prediction workflow, handles Label Studio request/response format
- `gemini_service.py` - Interfaces with Google Gemini AI for audio analysis
- `audio_handler.py` - Downloads and processes audio files, manages temporary storage

**Configuration (`app/`):**
- `config.py` - Centralized configuration using Pydantic Settings
- `config_patch.py` - Configuration patches and overrides

**Core Infrastructure (`app/core/`):**
- `logging.py` - Structured logging with JSON formatting
- `monitoring.py` - Prometheus metrics and health checks
- `exceptions.py` - Custom exception hierarchy

**Models (`app/models/`):**
- `api.py` - Pydantic models for API requests/responses, Label Studio format compliance

### Key Design Patterns

1. **Label Studio ML Backend Compliance**: The API strictly follows Label Studio's ML backend specification with `/predict`, `/setup`, and `/train` endpoints.

2. **Asynchronous Processing**: Uses FastAPI's async capabilities for non-blocking I/O operations, especially for audio downloading and AI model calls.

3. **Health Monitoring**: Implements comprehensive health checks for all services with Prometheus metrics exposed at `/metrics`.

4. **Temporary File Management**: Audio files are downloaded to `/tmp/audio_analysis/`, processed, and automatically cleaned up after use.

5. **Error Handling**: Centralized exception handling with structured error responses and proper HTTP status codes.

### Critical Configuration

**Required Environment Variables:**
- `GEMINI_API_KEY` - Google AI Studio API key (required)
- `PORT` - Server port (default: 9090)
- `HOST` - Server host (default: 0.0.0.0)

**Important Files:**
- `.env` - Environment configuration (create from `env.example`)
- `docker-compose.yml` - Docker services configuration including Prometheus and optional Redis/Grafana
- `requirements.txt` - Python dependencies

### Label Studio Integration Flow

1. Label Studio sends prediction request with task data to `/predict`
2. API extracts audio URL from task data
3. Audio file is downloaded to temporary storage
4. Gemini AI processes the audio for transcription, diarization, language detection, etc.
5. Results are formatted according to Label Studio's expected response format
6. Temporary audio file is cleaned up
7. Predictions are returned to Label Studio for annotation

### Docker Deployment

The project includes a complete Docker setup with:
- Main API service (`labelstudio-audio-api`)
- Prometheus metrics collection
- Optional Redis caching (profile: `with-redis`)
- Optional Grafana dashboards (profile: `with-grafana`)