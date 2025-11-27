#!/bin/bash
echo "Testing prediction endpoint..."
curl -X POST http://localhost:9090/predict \
  -H "Content-Type: application/json" \
  -d '{"tasks": [{"id": 1, "data": {"audio": "/test.mp3"}}]}' \
  2>/dev/null | python3 -m json.tool