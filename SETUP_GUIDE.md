# Setup Guide

## Important: About the `agents` Library

Your code uses the `agents` library from **OpenAI's Agent Builder** platform, which is a proprietary SDK for building AI agents with tools like FileSearch and WebSearch. This is **NOT** the public `agents` package on PyPI (which is for reinforcement learning).

## Quick Setup (Test Version) - RECOMMENDED

The test version works immediately without any complex setup and demonstrates all the web app functionality.

### 1. Install Minimal Dependencies

```bash
pip install -r requirements-test.txt
```

Or install manually:
```bash
pip install fastapi uvicorn[standard] pydantic
```

### 2. Run the Test Server

```bash
python3 app_test.py
```

You should see:
```
Starting test server on http://localhost:8000
This is a TEST version with mock responses.
Install the 'agents' library for full functionality.
INFO:     Uvicorn running on http://0.0.0.0:8000 (Press CTRL+C to quit)
```

### 3. Open Your Browser

Navigate to: **http://localhost:8000**

### 4. Try It Out!

The test version includes realistic mock responses for:
- **Injury recovery questions** - e.g., "How do I recover from an injury?"
- **Marathon training** - e.g., "How should I train for a marathon?"
- **Nutrition advice** - e.g., "What should I eat before running?"
- **General queries** - Any other question gets a friendly response

All features work:
- ✅ Session management
- ✅ Conversation context preservation
- ✅ Follow-up questions
- ✅ Reset functionality
- ✅ Clean UI with light background

## Production Setup (With OpenAI Agent Builder)

### Prerequisites

1. Access to OpenAI's Agent Builder platform
2. The OpenAI agents SDK properly configured
3. Valid vector store with your WhatsApp chat data
4. API credentials configured

### Installation

The production version requires the OpenAI agents library, which needs to be installed according to OpenAI's documentation (not from PyPI).

Once you have the agents library set up:

```bash
# Install web framework dependencies
pip install fastapi uvicorn[standard] pydantic pandas

# Run the production app
python3 app.py
```

### Configuration

Ensure these are configured in your environment:

1. **Vector Store ID**: Currently set to `vs_68e665b3074c8191b6655dc14c46dca0`
2. **Workflow ID**: `wf_68e4efaf64ac8190936826ade60fd3910d7efe675e39fbd9`
3. **API Credentials**: As required by OpenAI's agents SDK

## Comparison: Test vs Production

| Feature | Test Version | Production Version |
|---------|--------------|-------------------|
| Installation | Simple (3 packages) | Complex (requires OpenAI SDK) |
| Responses | Mock (realistic) | Real AI agents |
| WhatsApp Search | Simulated | Actual vector search |
| Web Search | Simulated | Real web search |
| Setup Time | 1 minute | Varies (requires API access) |
| Cost | Free | Varies (API usage) |
| Functionality | 100% UI/UX | 100% UI/UX + AI |

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'agents'`

This is expected if you don't have OpenAI's agents SDK installed. Use the test version instead:
```bash
python3 app_test.py
```

### Issue: Port 8000 already in use

Kill the existing process:
```bash
lsof -ti:8000 | xargs kill -9
```

### Issue: Can't find static/index.html

Make sure you're running from the project directory:
```bash
cd "/path/to/Whatsapp Summarizer"
python3 app_test.py
```

## Development

### Running with Auto-Reload

```bash
uvicorn app_test:app --reload --host 0.0.0.0 --port 8000
```

### Testing the API Directly

```bash
# Health check
curl http://localhost:8000/health

# Send a message
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I train for a marathon?"}'

# Reset session
curl -X POST http://localhost:8000/reset \
  -H "Content-Type: application/json" \
  -d '{"session_id": "your-session-id"}'
```

## Next Steps

1. **Test the UI**: Run `python3 app_test.py` and open http://localhost:8000
2. **Try Conversations**: Ask multiple follow-up questions to test context preservation
3. **Test Reset**: Clear the conversation and start fresh
4. **Deploy** (Optional): Deploy to a cloud platform for remote access
5. **Upgrade to Production**: When ready, set up OpenAI's agents SDK for real AI responses

## Files Overview

- `app_test.py` - Test version with mock responses (fully functional UI)
- `app.py` - Production version with real AI agents (requires OpenAI SDK)
- `static/index.html` - Single-page chat interface
- `requirements-test.txt` - Minimal dependencies for test version
- `requirements.txt` - Full dependencies (except OpenAI agents SDK)
- `Whatsapp.py` - Original standalone script
- `Whatsapp.ipynb` - Jupyter notebook for experimentation
