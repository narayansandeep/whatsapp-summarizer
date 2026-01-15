# Production Setup Guide

This guide explains how to set up the WhatsApp Running Coach with local vector database and OpenAI API.

## Overview

The production system consists of two parts:

1. **whatsappvector.py** - Creates a local vector database from WhatsApp chat data
2. **app_prod.py** - Chat application that uses OpenAI API with the vector database

## Architecture

```
WhatsApp Chat Folder (_chat.txt)
         ↓
   whatsappvector.py (run once or when chat updates)
         ↓
    VectorDB/ (ChromaDB)
         ↓
    app_prod.py (chat application)
         ├→ Searches VectorDB for relevant context
         ├→ Sends context + question to OpenAI API
         └→ Returns AI response to user
```

## Prerequisites

1. **OpenAI API Key** - You need an OpenAI API key
2. **WhatsApp Chat Export** - Chat data in "WhatsApp Chat" folder
3. **Python 3.9+** with pip

## Step 1: Install Dependencies

```bash
pip install -r requirements-prod.txt
```

Or install manually:
```bash
pip install fastapi uvicorn[standard] pydantic openai chromadb
```

## Step 2: Set OpenAI API Key

### macOS/Linux:
```bash
export OPENAI_API_KEY='your-api-key-here'
```

To make it permanent, add to your ~/.zshrc or ~/.bashrc:
```bash
echo 'export OPENAI_API_KEY="your-api-key-here"' >> ~/.zshrc
source ~/.zshrc
```

### Windows:
```cmd
set OPENAI_API_KEY=your-api-key-here
```

Or set permanently in System Environment Variables.

### Alternative: Create .env file

Create a file called `.env` in the project directory:
```
OPENAI_API_KEY=your-api-key-here
```

Then load it before running:
```bash
export $(cat .env | xargs)
```

## Step 3: Create Vector Database

Run the vector database creator script:

```bash
python3 whatsappvector.py
```

This will:
1. Read all messages from `WhatsApp Chat/_chat.txt`
2. Parse and clean the messages
3. Create message chunks (groups of 5 messages)
4. Generate embeddings using OpenAI API
5. Store in ChromaDB at `VectorDB/`

### Expected Output:
```
============================================================
WhatsApp Chat Vector Database Creator
============================================================

[Step 1/3] Reading WhatsApp chat...
Reading chat file: WhatsApp Chat/_chat.txt
Parsed 1234 messages

[Step 2/3] Chunking messages...
Created 247 message chunks

[Step 3/3] Creating vector database...
Initializing ChromaDB in VectorDB
Generating embeddings using OpenAI...
Processed batch 1/3
Processed batch 2/3
Processed batch 3/3
✅ Vector database created successfully with 247 chunks

============================================================
✅ SUCCESS!
============================================================
Total messages parsed: 1234
Total chunks created: 247
Vector database location: VectorDB/
Collection name: whatsapp_running_chat

You can now run the chat application:
  python3 app_prod.py
============================================================
```

### Cost Estimate

Using `text-embedding-3-small`:
- Cost: ~$0.02 per 1 million tokens
- Average chat: ~1000-2000 messages = ~$0.01-0.02
- **Very affordable!**

## Step 4: Run the Chat Application

```bash
python3 app_prod.py
```

### Expected Output:
```
============================================================
WhatsApp Running Coach - Production Server
============================================================
Vector DB: /path/to/VectorDB
Starting server on http://localhost:8000
============================================================
✅ Loaded vector database: whatsapp_running_chat
INFO:     Uvicorn running on http://0.0.0.0:8000
```

Open your browser to: **http://localhost:8000**

## Testing the Setup

### 1. Health Check
```bash
curl http://localhost:8000/health
```

Expected response:
```json
{
  "status": "healthy",
  "sessions": 0,
  "vector_db": "available",
  "vector_db_items": 247
}
```

### 2. Test Query
```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "How do I recover from a running injury?"}'
```

## How It Works

### When a user asks a question:

1. **Embedding Generation**
   - User's question is converted to embedding using OpenAI

2. **Vector Search**
   - ChromaDB finds the 5 most relevant WhatsApp chat excerpts

3. **Context Building**
   - Relevant chat messages are formatted as context

4. **AI Response**
   - Context + conversation history + question sent to OpenAI
   - GPT-4o-mini generates response based on WhatsApp chat context

5. **Session Management**
   - Conversation history maintained for follow-up questions

## Updating the Vector Database

When you have new WhatsApp chat data:

1. Export new WhatsApp chat to "WhatsApp Chat" folder
2. Run: `python3 whatsappvector.py`
3. Restart: `python3 app_prod.py`

The script will:
- Delete old vector database
- Create fresh database with all messages
- Preserve existing chat conversations (sessions are in memory)

## Cost Considerations

### Vector Database Creation (one-time):
- ~$0.01-0.02 for 1000-2000 messages
- Run only when chat updates

### Chat Application (per query):
- Embedding: ~$0.00001 per query
- GPT-4o-mini: ~$0.0001-0.0005 per query
- **Total: ~$0.001 per conversation**

### Monthly Estimate (100 queries/day):
- ~$3-5 per month

## Features

✅ **Local Vector Database** - No external vector DB service needed
✅ **Fast Retrieval** - ChromaDB optimized for speed
✅ **Context-Aware** - AI has access to relevant chat history
✅ **Conversation Memory** - Maintains session context
✅ **Cost Effective** - Only OpenAI API costs
✅ **Easy Updates** - Re-run script to update database

## Troubleshooting

### Issue: "OPENAI_API_KEY environment variable not set"
```bash
export OPENAI_API_KEY='your-key-here'
```

### Issue: "Chat file not found"
Ensure `WhatsApp Chat/_chat.txt` exists

### Issue: "Vector database not found"
Run `python3 whatsappvector.py` first

### Issue: "Collection 'whatsapp_running_chat' not found"
The vector DB creation failed. Check:
1. OpenAI API key is valid
2. You have API credits
3. Re-run `python3 whatsappvector.py`

### Issue: Rate limits from OpenAI
The script processes in batches of 100. If you hit rate limits:
1. Reduce batch_size in whatsappvector.py (line 145)
2. Add sleep between batches

## Files

- **whatsappvector.py** - Vector database creator (run when chat updates)
- **app_prod.py** - Production chat application
- **app_test.py** - Test version with mock responses (no API needed)
- **requirements-prod.txt** - Production dependencies
- **VectorDB/** - Local vector database (created by script)
- **WhatsApp Chat/_chat.txt** - Source WhatsApp chat data

## Comparison with Test Version

| Feature | Test Version | Production Version |
|---------|--------------|-------------------|
| Setup | Simple | Requires API key |
| Responses | Mock | Real AI |
| WhatsApp Search | Simulated | Real vector search |
| Cost | Free | ~$3-5/month |
| Accuracy | Generic | Specific to your chat |
| Updates | N/A | Re-run script |

## Next Steps

1. Set your OpenAI API key
2. Run `python3 whatsappvector.py`
3. Run `python3 app_prod.py`
4. Open http://localhost:8000
5. Ask questions about running training!

## Support

If you encounter issues:
1. Check API key is set correctly
2. Verify chat file exists
3. Check health endpoint: `curl http://localhost:8000/health`
4. Look for errors in terminal output
