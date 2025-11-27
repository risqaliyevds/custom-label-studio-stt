#!/usr/bin/env python3
"""Test script to verify the enhanced API with local audio file"""

import sys
import os
import json

# Add src to path
sys.path.insert(0, '/mnt/mata/labelStudio/src')

# Import the analyze function directly
from enhanced_api import analyze_audio_with_gemini

# Test with local audio file
test_file = "/mnt/mata/labelStudio/venv/lib/python3.13/site-packages/label_studio/core/static/samples/sample.mp3"

if os.path.exists(test_file):
    print(f"Testing with file: {test_file}")
    try:
        result = analyze_audio_with_gemini(test_file)
        print("\nAnalysis Result:")
        print(json.dumps(result, indent=2, ensure_ascii=False))
    except Exception as e:
        print(f"Error during analysis: {e}")
else:
    print(f"Test file not found: {test_file}")