# Label Studio Integration Guide

Complete guide for integrating the Audio Analysis API with Label Studio.

## Integration Steps

### 1. Start Your ML Backend

Make sure your API is running on the correct port:

```bash
# Option 1: Using the startup script
GEMINI_API_KEY="your_key" ./start_api.sh

# Option 2: Direct Python execution
source venv/bin/activate
GEMINI_API_KEY="your_key" python main.py --host 0.0.0.0 --port 9090

# Option 3: Using Docker
docker compose up -d
```

Verify it's working:
```bash
curl http://localhost:9090/
# Should return: {"model_class":"GeminiAudioMLBackend","status":"UP",...}
```

### 2. Connect to Label Studio

1. **Open Label Studio** and create or open your audio project
2. **Go to Settings** → **Machine Learning**
3. **Click "Connect Model"**
4. **Fill in the connection details:**

| Field | Value |
|-------|-------|
| **Name** | `Gemini Audio Analysis` |
| **Backend URL** | `http://localhost:9090` |
| **Authentication** | Leave blank (no authentication required) |
| **Interactive preannotations** | ✅ Enable (optional) |

5. **Click "Validate and Save"**

### 3. Expected Label Studio Response

When Label Studio connects, it will:
- Call `GET /` to check status
- Call `POST /setup` to get capabilities
- Call `POST /predict` when processing tasks

## 📡 API Endpoints

### Root Endpoint (`GET /`)
Returns ML backend status in Label Studio format:
```json
{
  "model_class": "GeminiAudioMLBackend",
  "status": "UP",
  "capabilities": ["transcription", "speaker_diarization", ...]
}
```

### Setup Endpoint (`POST /setup`)
Returns backend capabilities:
```json
{
  "model_version": "gemini-audio-analyzer-v2.0",
  "setup": "complete",
  "capabilities": ["transcription", "speaker_diarization", ...],
  "supported_formats": ["mp3", "wav", "m4a", "flac", "ogg", "aac"]
}
```

### Predict Endpoint (`POST /predict`)
**Request Format:**
```json
{
  "tasks": [
    {
      "id": 1,
      "data": {
        "audio": "path/to/audio.wav"
      }
    }
  ]
}
```

**Response Format:**
```json
{
  "results": [
    {
      "result": [
        {
          "value": {
            "start": 0.0,
            "end": 5.2,
            "text": ["Transcribed text"],
            "channel": 0
          },
          "from_name": "transcription",
          "to_name": "audio",
          "type": "textarea",
          "confidence": 0.95
        }
      ],
      "score": 0.95,
      "model_version": "gemini-audio-analyzer-v2.0"
    }
  ]
}
```

## 🔧 Troubleshooting

### Common Connection Issues

**1. Connection Refused**
- Ensure API is running: `curl http://localhost:9090/`
- Check port conflicts: `netstat -tulpn | grep 9090`
- Try different port: `PORT=9091 ./start_api.sh`

**2. Docker Container Issues**
If running Label Studio in Docker, use `host.docker.internal:9090` instead of `localhost:9090`

**3. API Key Errors**
- Verify Gemini API key: `echo $GEMINI_API_KEY`
- Check API key validity at [Google AI Studio](https://aistudio.google.com/)

**4. 422 Validation Errors**
- Ensure audio files are accessible
- Check audio format is supported
- Verify task data contains `audio` field

### Testing the Connection

Test each endpoint manually:

```bash
# Test status
curl http://localhost:9090/

# Test setup
curl -X POST http://localhost:9090/setup

# Test prediction
curl -X POST http://localhost:9090/predict \
  -H "Content-Type: application/json" \
  -d '{"tasks": [{"id": 1, "data": {"audio": "test.wav"}}]}'
```

## 🎯 Features Provided

Your ML backend provides these analysis capabilities:

- **Audio Transcription** with timestamps
- **Speaker Diarization** (who spoke when)
- **Language Detection** 
- **Gender Classification**
- **Emotion Analysis**
- **Named Entity Recognition**
- **Content Summarization**

## 📝 Label Configuration Example

For your audio project, use a labeling configuration like:

```xml
<View>
  <Audio name="audio" value="$audio"/>
  <TextArea name="transcription" toName="audio" 
            placeholder="Transcription will appear here..."/>
  <Labels name="speaker_labels" toName="audio">
    <Label value="Speaker 1"/>
    <Label value="Speaker 2"/>
  </Labels>
  <Choices name="language" toName="audio">
    <Choice value="English"/>
    <Choice value="Spanish"/>
    <Choice value="French"/>
  </Choices>
</View>
```

## 🚀 Next Steps

1. **Test with Real Audio**: Upload actual audio files to Label Studio
2. **Enable Auto-labeling**: Go to Settings → Annotation → "Use predictions to prelabel tasks"
3. **Review Predictions**: Check the quality of generated predictions
4. **Customize**: Modify the API to match your specific labeling schema

Your ML backend is now fully compatible with Label Studio! 🎉
