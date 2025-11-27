#!/usr/bin/env python3
"""
Test script for enhanced API with direct audio file
"""

import requests
import json
import os

# API endpoint
url = "http://localhost:9090/predict"

# Test data with different audio path formats
test_cases = [
    {"id": 1, "data": {"audio": "test.mp3"}},  # Just filename
    {"id": 2, "data": {"audio": "/test.mp3"}},  # With leading slash
    {"id": 3, "data": {"audio": "file:///mnt/mata/labelStudio/test.mp3"}},  # File URL
]

for test in test_cases:
    print(f"\nTesting with: {test['data']['audio']}")
    print("-" * 50)
    
    response = requests.post(url, json={"tasks": [test]})
    
    if response.status_code == 200:
        result = response.json()
        if result.get("results") and result["results"][0].get("result"):
            print("Success! Got predictions:")
            predictions = result["results"][0]["result"]
            
            # Count predictions by type
            types = {}
            for pred in predictions:
                pred_type = pred.get("from_name", "unknown")
                types[pred_type] = types.get(pred_type, 0) + 1
            
            print(f"Predictions by type: {types}")
            
            # Show first few predictions
            for i, pred in enumerate(predictions[:3]):
                print(f"  Prediction {i+1}: {pred.get('from_name')} = {pred.get('value')}")
        else:
            print("No predictions returned")
            print(f"Response: {json.dumps(result, indent=2)}")
    else:
        print(f"Error: {response.status_code}")
        print(f"Response: {response.text}")