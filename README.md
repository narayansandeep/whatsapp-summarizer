# WhatsApp Running Coach Chat Assistant

An AI-powered chat assistant that answers running training questions by searching through a running group's WhatsApp chat history using local vector database and OpenAI API.

## Quick Start

### Option 1: Production Version (Recommended)

Uses OpenAI API with local ChromaDB vector database for accurate, context-aware responses.

```bash
# 1. Install dependencies
pip install -r requirements-prod.txt

# 2. Set your OpenAI API key
export OPENAI_API_KEY='your-api-key-here'

# 3. Create vector database from WhatsApp chat (first time only)
python3 whatsappvector.py

# 4. Start the application
python3 app_prod.py
```

Then open your browser to: `http://localhost:8000`

**Cost**: ~$0.01 to create vector DB, ~$0.001 per conversation (~$3-5/month for regular use)

### Option 2: Test Version (Free, No API Key)

Test the UI with mock responses (no real AI, no API costs).

```bash
# Install minimal dependencies
pip install fastapi uvicorn[standard] pydantic

# Run test server
python3 app_test.py
```

Then open your browser to: `http://localhost:8000`

## Features

- **Conversational Interface**: Chat naturally with the AI assistant
- **Context Preservation**: Ask follow-up questions that reference previous messages
- **Smart Routing**: Questions are automatically routed to specialized agents:
  - Training questions → searches WhatsApp chat history
  - Event queries → searches the web for current information
  - Other queries → polite fallback response
- **Session Management**: Each conversation is saved during your session
- **Simple Reset**: Clear your conversation history and start fresh anytime

## Usage Examples

Try asking questions like:
- "What's the best way to recover from an injury?"
- "How should I prepare for a marathon?"
- "What nutrition advice is recommended for long runs?"
- "Tell me about upcoming running events in Mumbai"

## Updating Chat Data

When you get new WhatsApp chat exports:

1. Export WhatsApp chat and place `_chat.txt` in `WhatsApp Chat/` folder
2. Run: `python3 whatsappvector.py`
3. Restart: `python3 app_prod.py`

The vector database will be rebuilt with all the latest messages.

## Project Structure

```
├── whatsappvector.py     # Creates vector DB from WhatsApp chat
├── app_prod.py           # Production app with OpenAI + vector DB
├── app_test.py           # Test app with mock responses
├── app.py                # Legacy OpenAI Agent Builder version
├── Whatsapp.py           # Original standalone script
├── Whatsapp.ipynb        # Jupyter notebook for experimentation
├── WhatsApp Chat/
│   └── _chat.txt         # WhatsApp chat export file
├── VectorDB/             # ChromaDB vector database (created by script)
├── static/
│   └── index.html        # Chat interface UI
├── requirements-prod.txt # Production dependencies
├── requirements-test.txt # Test dependencies
├── PRODUCTION_SETUP.md   # Detailed production setup guide
├── CLAUDE.md             # Developer documentation
└── README.md             # This file
```

## Technical Details

### Production Version
- **Framework**: FastAPI with async/await support
- **AI Model**: GPT-4o-mini (fast and cost-effective)
- **Embeddings**: OpenAI text-embedding-3-small
- **Vector Database**: ChromaDB (local, persistent)
- **Session Storage**: In-memory with automatic cleanup (1 hour expiry)
- **Frontend**: Vanilla JavaScript with responsive design

### How It Works
1. User asks a question
2. Question is embedded using OpenAI
3. ChromaDB finds 5 most relevant WhatsApp chat excerpts
4. Context + question sent to GPT-4o-mini
5. AI generates response based on real chat conversations
6. Session maintains context for follow-up questions

## Development

For detailed architecture and development information, see [CLAUDE.md](CLAUDE.md).

To run in development mode with auto-reload:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```
