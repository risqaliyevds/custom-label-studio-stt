#!/bin/bash
# Start the Label Studio Audio Analysis API
#
# Usage:
#   ./start_api.sh                    # Start with default settings
#   GEMINI_API_KEY=your_key ./start_api.sh  # Start with custom API key
#
# Make sure to set your Gemini API key either:
# 1. In the .env file: GEMINI_API_KEY=your_key_here
# 2. As environment variable: export GEMINI_API_KEY=your_key_here
# 3. Pass it when running: GEMINI_API_KEY=your_key ./start_api.sh

set -e

# Activate virtual environment
source venv/bin/activate

# Check if API key is set
if [ -z "$GEMINI_API_KEY" ]; then
    echo "⚠️  GEMINI_API_KEY not set as environment variable"
    echo "   Checking .env file..."
    if [ -f ".env" ] && grep -q "GEMINI_API_KEY=" .env; then
        echo "   ✅ Found GEMINI_API_KEY in .env file"
    else
        echo "   ❌ GEMINI_API_KEY not found in .env file"
        echo ""
        echo "Please set your Gemini API key:"
        echo "  1. Add to .env file: GEMINI_API_KEY=your_key_here"
        echo "  2. Or export as env var: export GEMINI_API_KEY=your_key_here"
        echo "  3. Or pass when running: GEMINI_API_KEY=your_key ./start_api.sh"
        exit 1
    fi
fi

echo "🚀 Starting Label Studio Audio Analysis API..."
echo "   Host: ${HOST:-0.0.0.0}"
echo "   Port: ${PORT:-9090}"
echo ""

# Start the API
python main.py --host "${HOST:-0.0.0.0}" --port "${PORT:-9090}"
