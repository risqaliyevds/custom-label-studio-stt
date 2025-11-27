# Simple Label Studio ML Backend for Gemini Audio Analysis

A minimal, working implementation of a Label Studio ML backend that uses Google's Gemini API for audio analysis and prediction.

## Features

✅ **Minimal & Clean** - Single file implementation (`simple_api.py`)  
✅ **Label Studio Compatible** - Follows ML backend specification  
✅ **Gemini Powered** - Uses Gemini 1.5 Flash for audio analysis  
✅ **Audio Analysis** - Transcription, speaker detection, language, emotion  

## Quick Start

### 1. Set up Gemini API Key

Get your API key from [Google AI Studio](https://aistudio.google.com/apikey)

```bash
export GEMINI_API_KEY=your_api_key_here
```

Or add to `.env` file:
```
GEMINI_API_KEY=your_api_key_here
```

### 2. Run the API

```bash
# Quick start
./run_simple.sh

# Or manually
python simple_api.py
```

The API will start on `http://localhost:9090`

### 3. Connect to Label Studio

1. Open Label Studio
2. Go to **Settings** → **Machine Learning**
3. Click **Add Model**
4. Enter URL: `http://localhost:9090`
5. Click **Validate and Save**

## API Endpoints

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/predict` | POST | Generate predictions |
| `/setup` | POST | ML backend setup |

## Prediction Request Format

Label Studio sends requests in this format:

```json
{
  "tasks": [
    {
      "id": 1,
      "data": {
        "audio": "/path/to/audio.mp3"
      }
    }
  ]
}
```

## Prediction Response Format

The API returns predictions in Label Studio format:

```json
{
  "results": [
    {
      "result": [
        {
          "value": {
            "start": 0,
            "end": 5.2,
            "text": ["transcribed text"],
            "channel": 0
          },
          "from_name": "transcription",
          "to_name": "audio",
          "type": "textarea",
          "origin": "prediction"
        }
      ],
      "score": 0.95,
      "model_version": "gemini-1.5-flash"
    }
  ]
}
```

## Testing

Test the API with the provided script:

```bash
# Make sure API is running first
python test_predict.py
```

## Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `GEMINI_API_KEY` | Required | Google AI API key |
| `PORT` | 9090 | API port |
| `HOST` | 0.0.0.0 | API host |
| `LABEL_STUDIO_URL` | http://localhost:8080 | Label Studio URL |
| `LABEL_STUDIO_API_KEY` | Optional | Label Studio API key |

## Label Studio Configuration

Example labeling configuration for audio analysis:

```xml
<View>
  <Audio name="audio" value="$audio"/>
  
  <TextArea name="transcription" toName="audio" 
            showSubmitButton="false" maxSubmissions="1" 
            editable="true"/>
  
  <Choices name="language" toName="audio" choice="single">
    <Choice value="English"/>
    <Choice value="Spanish"/>
    <Choice value="French"/>
    <Choice value="Other"/>
  </Choices>
  
  <Choices name="emotion" toName="audio" choice="single">
    <Choice value="neutral"/>
    <Choice value="happy"/>
    <Choice value="sad"/>
    <Choice value="angry"/>
  </Choices>
  
  <TextArea name="summary" toName="audio"/>
</View>
```

## How It Works

1. **Label Studio** sends audio file path/URL to `/predict`
2. **API** downloads the audio file
3. **Gemini** analyzes the audio (transcription, language, emotion, etc.)
4. **API** formats results for Label Studio
5. **Label Studio** displays predictions for review/correction

## Troubleshooting

### API won't start
- Check `GEMINI_API_KEY` is set correctly
- Verify port 9090 is not in use

### No predictions returned
- Check API logs for errors
- Verify audio file is accessible
- Test with `test_predict.py`

### Label Studio connection fails
- Ensure API is running on correct port
- Check firewall/network settings
- Verify URL in Label Studio settings

## Files

- `simple_api.py` - Main API implementation
- `run_simple.sh` - Startup script
- `test_predict.py` - Test script
- `test.mp3` - Sample audio for testing

## Requirements

- Python 3.8+
- Gemini API key
- Label Studio (for integration)

## License

MIT