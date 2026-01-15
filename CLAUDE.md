# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project Overview

This is a WhatsApp chat analyzer for a running group that answers training-related questions by searching through historical WhatsApp chat data using a local vector database and OpenAI API. The project includes a web application with a chat interface.

### Two Versions Available:
1. **Production Version** (`app_prod.py`) - Uses OpenAI API with local ChromaDB vector database
2. **Test Version** (`app_test.py`) - Mock responses for testing UI without API costs

## Architecture

### Production Architecture (app_prod.py)

The current production system uses a two-step approach:

```
WhatsApp Chat Folder → whatsappvector.py → ChromaDB Vector Database → app_prod.py
                                                                              ↓
                                                                    User Query
                                                                              ↓
                                                          Vector Search (find relevant context)
                                                                              ↓
                                                              OpenAI API (GPT-4o-mini)
                                                                              ↓
                                                                    AI Response
```

**Key Components:**
1. **whatsappvector.py** - Parses WhatsApp chat and creates vector database
   - Reads `WhatsApp Chat/_chat.txt`
   - Chunks messages (groups of 5)
   - Generates embeddings using OpenAI `text-embedding-3-small`
   - Stores in ChromaDB at `VectorDB/`

2. **app_prod.py** - FastAPI web application
   - Loads ChromaDB vector database
   - For each query: searches vector DB for relevant context
   - Sends context + question to OpenAI API
   - Returns AI-generated response
   - Maintains session history for follow-up questions

### Legacy: Multi-Agent Workflow System (Original)

The application uses a multi-agent architecture built with the `agents` library (appears to be an OpenAI Agents/Assistant API wrapper). The workflow consists of 4 specialized agents:

1. **Greeting Agent** (`greeting`):
   - Entry point for all user queries
   - Extracts intent from user input using structured output (GreetingSchema)
   - Returns two fields: `training_goal` (training-related questions) and `event_info` (running event queries)
   - Uses GPT-4.1-mini with structured output

2. **Training Info Agent** (`training_info`):
   - Answers training-related questions using the WhatsApp chat history
   - Uses FileSearchTool connected to vector store: `vs_68e665b3074c8191b6655dc14c46dca0`
   - The vector store contains the running group's WhatsApp chat data

3. **Event Name Agent** (`event_name`):
   - Handles queries about running events
   - Uses WebSearchTool to fetch current event information from the internet

4. **Fallback Agent** (`agent`):
   - Handles queries that don't match training or event categories
   - Politely declines to answer

### Workflow Routing Logic

The `run_workflow` function implements a simple routing pattern:
```
User Input → Greeting Agent → Parse Intent
                              ↓
              ┌───────────────┼───────────────┐
              ↓               ↓               ↓
     training_goal != ""  event_info != ""  else
              ↓               ↓               ↓
      Training Info      Event Name      Fallback
          Agent             Agent          Agent
```

**Important**: The current implementation has a bug in line 154 where `event_info` routing checks `training_goal` instead of `event_info`.

### Data Flow

1. WhatsApp chat data is stored in `WhatsappChat.txt` (330KB text file)
2. The notebook `Whatsapp.ipynb` contains parsing logic that extracts structured messages using regex: `^(\d{1,2}/\d{1,2}/\d{2,4}), (\d{1,2}:\d{2}) - (.*?): (.*)$`
3. Parsed data creates a DataFrame with columns: date, time, sender, text
4. The chat data is uploaded to OpenAI's vector store for semantic search

## Running the Application

### Production Version with Vector DB (Recommended)

**First time setup:**
```bash
# 1. Install dependencies
pip install -r requirements-prod.txt

# 2. Set OpenAI API key
export OPENAI_API_KEY='your-api-key-here'

# 3. Create vector database (run once or when chat updates)
python3 whatsappvector.py

# 4. Start the application
python3 app_prod.py
```

**Subsequent runs:**
```bash
# Just start the app (vector DB already exists)
python3 app_prod.py
```

**When chat data updates:**
```bash
# Re-create vector database
python3 whatsappvector.py

# Restart application
python3 app_prod.py
```

Access at: `http://localhost:8000`

### Test Version (No API Key Needed)

The application now runs as a FastAPI web server with a chat interface.

**Install dependencies:**
```bash
pip install -r requirements.txt
```

**Start the server:**
```bash
python app.py
```

Or using uvicorn directly:
```bash
uvicorn app:app --reload --host 0.0.0.0 --port 8000
```

**Access the application:**
Open your browser to `http://localhost:8000`

**Features:**
- Chat interface with conversation history
- Session management (sessions expire after 1 hour of inactivity)
- Reset button to clear conversation and start fresh
- Preserves context for follow-up questions

**API Endpoints:**
- `GET /` - Serves the chat interface
- `POST /chat` - Send a message and get a response
  - Request: `{"message": "string", "session_id": "optional_string"}`
  - Response: `{"response": "string", "session_id": "string"}`
- `POST /reset` - Reset a session's conversation history

### Legacy Script Execution
```bash
python Whatsapp.py
```

The script includes a sample execution in `__main__` that runs:
```python
sample_input = WorkflowInput(input_as_text="Hello, I'm training for a marathon. Can you help me with my training plan?")
result = asyncio.run(run_workflow(sample_input))
```

### Jupyter Notebook Usage
The `Whatsapp.ipynb` notebook can be run interactively. Example usage:
```python
abc = await run_workflow(WorkflowInput(input_as_text="What is the best way to recover from injury?"))
print(abc["output_text"])
```

## Dependencies

The project depends on the `agents` library which provides:
- `FileSearchTool`, `WebSearchTool`: Tool integrations for agent capabilities
- `Agent`: Agent definition with instructions, model, and tools
- `ModelSettings`: Configuration for temperature, tokens, etc.
- `Runner`: Executes agent workflows
- `RunConfig`: Runtime configuration including trace metadata

Additional dependencies:
- `pydantic`: For structured data models (BaseModel)
- `asyncio`: Asynchronous workflow execution
- `pandas`, `re`: For WhatsApp chat parsing (in notebook)
- `fastapi`: Web framework for the chat application
- `uvicorn`: ASGI server to run the FastAPI app

## Key Configuration

- **Vector Store ID**: `vs_68e665b3074c8191b6655dc14c46dca0` - Contains the WhatsApp chat history
- **Workflow ID**: `wf_68e4efaf64ac8190936826ade60fd3910d7efe675e39fbd9` - Used for tracing
- **Model**: GPT-4.1-mini for most agents, GPT-4o-mini for fallback
- **Model Settings**: temperature=1, top_p=1, max_tokens=2048, store=True

## Web Application Architecture

The project has been successfully transformed into a web application with the following implementation:

### Backend (app.py)
- FastAPI application with async endpoints
- In-memory session management with automatic cleanup (sessions expire after 1 hour)
- Modified `run_workflow_with_history` function that accepts and maintains conversation history
- Fixed the bug in event_info routing (line 154 in original Whatsapp.py)

### Frontend (static/index.html)
- Single-page application with embedded CSS and JavaScript
- Clean, minimalist UI with light background gradient
- Real-time chat interface with smooth animations
- Loading indicators for better UX
- Reset functionality to clear conversation history

### Session Management
- Each user gets a unique session ID (UUID)
- Conversation history stored per session
- Automatic cleanup of inactive sessions (older than 1 hour)
- Session persists across multiple queries for contextual follow-up questions

## Future Enhancements

Potential improvements for the application:
- Persistent storage for conversations (database instead of in-memory)
- User authentication and personalized experiences
- Streaming responses for longer agent outputs
- Export chat history functionality
- Mobile-responsive design improvements
- Rate limiting and security enhancements
