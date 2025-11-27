# Label Studio Audio Analysis ML Backend

A robust ML backend for Label Studio that provides comprehensive audio analysis using Google's Gemini AI.

## 📁 Project Structure

```
labelStudio/
├── src/                    # Source code
│   ├── enhanced_api.py    # Enhanced API with advanced features
│   └── simple_api.py       # Simple API for basic functionality
├── tests/                  # Test files
│   ├── test_enhanced.py    # Tests for enhanced API
│   ├── test_predict.py     # General prediction tests
│   └── test_api.sh         # Shell test script
├── scripts/                # Utility scripts
│   ├── run_simple.sh       # Run simple API
│   ├── monitor_logs.sh    # Monitor logs
│   └── start_api.sh        # Start API server
├── docs/                   # Documentation
│   ├── CLAUDE.md          # Claude assistant notes
│   ├── LABEL_STUDIO_INTEGRATION.md
│   └── SIMPLE_API_README.md
├── logs/                   # Log files
├── venv/                   # Python virtual environment
├── .env                    # Environment configuration
├── requirements.txt        # Python dependencies
├── Dockerfile              # Docker configuration
└── docker-compose.yml      # Docker compose setup
```

## 🚀 Quick Start

### 1. Setup Environment

```bash
# Create and activate virtual environment
python3 -m venv venv
source venv/bin/activate

# Install dependencies
pip install -r requirements.txt
```

### 2. Configure Environment

Edit `.env` file with your credentials:
```env
GEMINI_API_KEY=your_gemini_api_key
LABEL_STUDIO_API_KEY=your_label_studio_token
GEMINI_MODEL=gemini-2.5-flash
```

### 3. Run the API

```bash
# Run enhanced API (recommended)
source venv/bin/activate
python src/enhanced_api.py

# Or run simple API
python src/simple_api.py
```

The API will start on `http://localhost:9090`

## 🎯 Features

### Enhanced API (`enhanced_api.py`)
- **Speaker Diarization**: Accurate speaker identification and tracking
- **Precise Timing**: Timestamps to 0.1 second precision
- **Multi-language Support**: 
  - Uzbek (Latin script)
  - Russian (Cyrillic)
  - Arabic
  - English
  - Turkish
- **Emotion Detection**: 11 emotion types with nuanced analysis
- **Gender Identification**: Accurate voice-based gender detection
- **Comprehensive Summaries**: Detailed summaries in Uzbek Latin

### Simple API (`simple_api.py`)
- Basic transcription
- Language detection
- Simple speaker identification
- Summary generation

## 🔌 Label Studio Integration

1. Start the ML backend:
```bash
python src/enhanced_api.py
```

2. In Label Studio, add ML backend:
   - Go to Project Settings → Machine Learning
   - Add URL: `http://localhost:9090`
   - Test connection

3. Use predictions:
   - Click "Predict" on tasks to get AI predictions
   - Review and correct predictions as needed

## 📊 API Endpoints

- `GET /` - Health check and status
- `POST /setup` - Initialize backend
- `POST /predict` - Generate predictions
- `GET /health` - Health status

## 🧪 Testing

```bash
# Run Python tests
python tests/test_enhanced.py

# Run shell tests
bash tests/test_api.sh
```

## 🐳 Docker Support

```bash
# Build and run with Docker Compose
docker-compose up --build
```

## 📝 Configuration

All configuration is managed through `.env` file:

- `GEMINI_API_KEY` - Google Gemini API key (required)
- `GEMINI_MODEL` - Model to use (default: gemini-2.5-flash)
- `LABEL_STUDIO_URL` - Label Studio URL (default: http://localhost:8080)
- `LABEL_STUDIO_API_KEY` - Label Studio API token
- `PORT` - API port (default: 9090)
- `HOST` - API host (default: 0.0.0.0)

## 🛠️ Development

The project uses:
- **FastAPI** for the web framework
- **Google Generative AI** for audio analysis
- **HTTPX** for async HTTP requests
- **Uvicorn** as ASGI server

## 📄 License

This project is configured for Label Studio audio analysis tasks.