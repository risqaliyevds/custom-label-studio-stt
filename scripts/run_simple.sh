#!/bin/bash
# Simple startup script for Label Studio ML Backend

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install requirements if needed
pip install -q fastapi uvicorn httpx google-generativeai pydantic aiofiles

# Check for API key
if [ -z "$GEMINI_API_KEY" ]; then
    # Try to load from .env file
    if [ -f ".env" ]; then
        export $(grep -v '^#' .env | xargs)
    fi
fi

if [ -z "$GEMINI_API_KEY" ]; then
    echo "❌ ERROR: GEMINI_API_KEY not set"
    echo ""
    echo "Please set your Gemini API key:"
    echo "  export GEMINI_API_KEY=your_api_key_here"
    echo "  ./run_simple.sh"
    echo ""
    echo "Or add it to .env file:"
    echo "  GEMINI_API_KEY=your_api_key_here"
    exit 1
fi

echo "✅ Starting Label Studio ML Backend (Simplified)"
echo "   Host: ${HOST:-0.0.0.0}"
echo "   Port: ${PORT:-9090}"
echo "   API Key: ${GEMINI_API_KEY:0:20}..."
echo ""
echo "📡 Endpoints:"
echo "   http://localhost:${PORT:-9090}/ - API info"
echo "   http://localhost:${PORT:-9090}/health - Health check"
echo "   http://localhost:${PORT:-9090}/predict - Predictions"
echo ""

# Run the simplified API
python simple_api.py