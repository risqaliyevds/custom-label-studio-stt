#!/usr/bin/env python3
"""
Test script for Label Studio ML Backend prediction endpoint
"""

import requests
import json
import sys
import os

# Configuration
API_URL = os.getenv("API_URL", "http://localhost:9090")


def test_health():
    """Test health endpoint"""
    print("Testing /health endpoint...")
    try:
        response = requests.get(f"{API_URL}/health")
        print(f"Status: {response.status_code}")
        print(f"Response: {response.json()}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_info():
    """Test root endpoint"""
    print("\nTesting / endpoint...")
    try:
        response = requests.get(f"{API_URL}/")
        print(f"Status: {response.status_code}")
        print(f"Response: {json.dumps(response.json(), indent=2)}")
        return response.status_code == 200
    except Exception as e:
        print(f"Error: {e}")
        return False


def test_predict_local():
    """Test predict endpoint with local file"""
    print("\nTesting /predict endpoint with local file...")
    
    # Create a Label Studio-like request
    request_data = {
        "tasks": [
            {
                "id": 1,
                "data": {
                    "audio": "/test.mp3"  # This would be the path in Label Studio
                }
            }
        ]
    }
    
    print(f"Request: {json.dumps(request_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{API_URL}/predict",
            json=request_data,
            headers={"Content-Type": "application/json"}
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            
            # Validate response structure
            if "results" in result and len(result["results"]) > 0:
                prediction = result["results"][0]
                if "result" in prediction:
                    print("\n✅ Prediction successful!")
                    print(f"Number of annotations: {len(prediction['result'])}")
                    return True
        else:
            print(f"Error response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    return False


def test_predict_url():
    """Test predict endpoint with URL"""
    print("\nTesting /predict endpoint with URL...")
    
    # Example with a public audio file URL
    request_data = {
        "tasks": [
            {
                "id": 2,
                "data": {
                    "audio": "https://www.soundhelix.com/examples/mp3/SoundHelix-Song-1.mp3"
                }
            }
        ]
    }
    
    print(f"Request: {json.dumps(request_data, indent=2)}")
    
    try:
        response = requests.post(
            f"{API_URL}/predict",
            json=request_data,
            headers={"Content-Type": "application/json"},
            timeout=60  # Longer timeout for download and processing
        )
        
        print(f"Status: {response.status_code}")
        
        if response.status_code == 200:
            result = response.json()
            print(f"Response: {json.dumps(result, indent=2)}")
            return True
        else:
            print(f"Error response: {response.text}")
            
    except Exception as e:
        print(f"Error: {e}")
    
    return False


def main():
    """Run all tests"""
    print(f"Testing ML Backend at {API_URL}")
    print("=" * 50)
    
    # Check if API is running
    try:
        response = requests.get(f"{API_URL}/health", timeout=2)
    except:
        print("❌ API is not running!")
        print(f"Please start the API first: ./run_simple.sh")
        return 1
    
    # Run tests
    tests = [
        ("Health Check", test_health),
        ("API Info", test_info),
        ("Predict (Local)", test_predict_local),
        # ("Predict (URL)", test_predict_url),  # Optional: test with external URL
    ]
    
    results = []
    for name, test_func in tests:
        print(f"\n{'=' * 50}")
        print(f"Running: {name}")
        print("-" * 50)
        success = test_func()
        results.append((name, success))
    
    # Summary
    print(f"\n{'=' * 50}")
    print("TEST SUMMARY")
    print("=" * 50)
    for name, success in results:
        status = "✅ PASS" if success else "❌ FAIL"
        print(f"{name}: {status}")
    
    # Overall result
    all_passed = all(success for _, success in results)
    if all_passed:
        print("\n🎉 All tests passed!")
        return 0
    else:
        print("\n❌ Some tests failed")
        return 1


if __name__ == "__main__":
    sys.exit(main())