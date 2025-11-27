# Label Studio Audio Analysis API

ML backend for Label Studio that provides audio analysis using Google's Gemini AI.

> **📌 Quick Start:** For a simplified, minimal implementation, use `simple_api.py` - see [SIMPLE_API_README.md](SIMPLE_API_README.md)

## Features

- Audio transcription with timestamps
- Speaker diarization and identification
- Language detection
- Gender classification
- Emotion analysis
- Content summarization
- Named entity recognition

## Quick Start

### Prerequisites

- Python 3.11+
- Google AI Studio API Key

### Installation

```bash
# Setup virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt

# Configure API key
cp env.example .env
# Edit .env and set GEMINI_API_KEY
```

### Running

```bash
# Start the API
./start_api.sh

# Or manually
python main.py --host 0.0.0.0 --port 9090
```

### Docker

```bash
docker compose up -d
```

## Label Studio Integration

1. Start the API on port 9090
2. In Label Studio: **Settings** → **Machine Learning**
3. Add model with URL: `http://localhost:9090`
4. Click **Validate and Save**

See [LABEL_STUDIO_INTEGRATION.md](./LABEL_STUDIO_INTEGRATION.md) for detailed setup.

## API Endpoints

- `GET /` - API information
- `GET /health` - Health check
- `POST /predict` - Generate predictions
- `POST /setup` - ML backend setup
- `GET /metrics` - System metrics

## Configuration

Required environment variable:
- `GEMINI_API_KEY` - Google AI Studio API key

Optional:
- `PORT` - Server port (default: 9090)
- `HOST` - Server host (default: 0.0.0.0)

See `env.example` for all options.

## License

MIT License