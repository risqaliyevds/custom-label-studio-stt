# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

Label Studio ML Backend for audio analysis using Google's Gemini AI. Provides transcription, speaker diarization, emotion detection, and multi-language support (Uzbek Latin, Russian Cyrillic, Arabic, English, Turkish).

## Commands

### Development
```bash
# Setup
python3 -m venv venv && source venv/bin/activate && pip install -r requirements.txt

# Run enhanced API (recommended)
python src/enhanced_api.py

# Run simple API (basic features only)
python src/simple_api.py
```

### Docker
```bash
# Build and start all services
docker build -t labelstudio-audio-api:latest . && docker compose up -d

# Or use the smart startup script
./start.sh

# View logs
docker compose logs -f labelstudio-audio-api
```

### Testing
```bash
python tests/test_enhanced.py
bash tests/test_api.sh
curl http://localhost:9090/health
```

## Architecture

### Two API Implementations

**Enhanced API** (`src/enhanced_api.py`): Full-featured with speaker diarization (0.1s precision), multi-language transcription, emotion detection (11 types), gender identification, and Uzbek summaries.

**Simple API** (`src/simple_api.py`): Basic transcription, language detection, and summary generation.

### Request Flow

1. Label Studio → POST `/predict` with audio URLs
2. Backend downloads audio (supports local files, URLs, Label Studio paths)
3. Gemini API analyzes audio with structured prompts
4. Results formatted as Label Studio predictions
5. Temp files cleaned up

### Key Files

- `src/enhanced_api.py` - Main API with Gemini analysis logic
- `docker-compose.yml` - Full stack: Label Studio, PostgreSQL, ML Backend, Backup
- `start.sh` - Smart startup with automatic backup restoration
- `template.xml` - Audio transcription labeling template

### Environment Variables

Required in `.env`:
- `GEMINI_API_KEY` - Google AI API key (required)
- `GEMINI_MODEL` - Model name (default: "gemini-2.0-flash")
- `LABEL_STUDIO_API_KEY` - For downloading audio from Label Studio

Optional:
- `PORT` / `HOST` - API server (default: 9090 / 0.0.0.0)
- `LABEL_STUDIO_URL` - Label Studio instance (default: http://localhost:8080)

### Docker Stack Services

- `label-studio` (port 8080) - Main annotation platform
- `postgres` - PostgreSQL database for Label Studio
- `labelstudio-audio-api` (port 9090) - This ML backend
- `backup-service` - Daily automated backups at 00:00 UTC

### Backup & Restore

```bash
# Manual backup
docker exec labelstudio-backup /backup.sh

# Restore from backup
./scripts/restore_backup.sh YYYY-MM-DD
```

## Important Notes

- Audio files downloaded to `/tmp/audio_analysis/` are auto-cleaned after processing
- Gemini safety filters may block content; fallback responses are returned in such cases
- The enhanced API uses retry logic (3 attempts) for Gemini API failures
- Summaries are always generated in Uzbek Latin script
