#!/bin/bash

# Label Studio Audio ML Backend Starter Script

echo "🚀 Starting Label Studio Audio ML Backend..."

# Check if virtual environment exists
if [ ! -d "venv" ]; then
    echo "📦 Creating virtual environment..."
    python3 -m venv venv
fi

# Activate virtual environment
source venv/bin/activate

# Install dependencies if needed
echo "📚 Checking dependencies..."
pip install -q -r requirements.txt

# Check for .env file
if [ ! -f ".env" ]; then
    echo "❌ Error: .env file not found!"
    echo "Please create a .env file with your GEMINI_API_KEY"
    exit 1
fi

# Stop any existing instances
echo "🛑 Stopping any existing instances..."
pkill -f enhanced_api.py 2>/dev/null
pkill -f simple_api.py 2>/dev/null

# Start the enhanced API
echo "✨ Starting Enhanced API on port 9090..."
python -m dotenv run python src/enhanced_api.py