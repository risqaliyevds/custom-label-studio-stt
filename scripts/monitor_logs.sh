#!/bin/bash
# Monitor API logs in real-time

echo "================================"
echo "  LABEL STUDIO ML BACKEND LOGS"
echo "================================"
echo ""
echo "Monitoring API on http://localhost:9090"
echo "Press Ctrl+C to stop monitoring"
echo ""
echo "Waiting for requests from Label Studio..."
echo "--------------------------------"

# Find the Python process and tail its output
PID=$(pgrep -f "simple_api.py" | head -1)

if [ -z "$PID" ]; then
    echo "API is not running! Starting it now..."
    source venv/bin/activate
    export GEMINI_API_KEY="AIzaSyAlBVW4srJ8r8SwL72aLhrfbUQAa1q7c-Y"
    export LABEL_STUDIO_API_KEY="eyJhbGciOiJIUzI1NiIsInR5cCI6IkpXVCJ9.eyJ0b2tlbl90eXBlIjoicmVmcmVzaCIsImV4cCI6ODA2NDcxMjY3NywiaWF0IjoxNzU3NTEyNjc3LCJqdGkiOiIzMjhkZmExMzg3NGU0Y2QzYjAyZmRlMmQ4NjEyMGYyYSIsInVzZXJfaWQiOiIxIn0.0VpbWfVFg_h-EBhaBbzTx2fS_vebmFLWjilyjXk-1QQ"
    python simple_api.py
else
    echo "API is running with PID: $PID"
    echo ""
    # Try to attach to the process output or show recent logs
    if [ -f api_output.log ]; then
        tail -f api_output.log
    else
        echo "Live logs (new requests will appear here):"
        echo ""
        # Monitor network traffic to the API
        while true; do
            curl -s http://localhost:9090/health > /dev/null 2>&1
            sleep 5
        done &
        
        # Show journalctl or any system logs if available
        tail -f /dev/null
    fi
fi