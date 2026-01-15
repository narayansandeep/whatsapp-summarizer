# Quick Start Guide

## Current Status ✅

Your production WhatsApp Running Coach is **ready and working!**

- ✅ Vector Database: 170 chunks from 850 messages
- ✅ Server running on: http://localhost:8000
- ✅ AI pulling real context from WhatsApp chat

## Test It Now!

Open your browser: **http://localhost:8000**

Try asking:
- "What did people say about hydration?"
- "What advice is there about recovery?"
- "Tell me about the long runs"

## Daily Usage

### Start the Server

```bash
# From project directory
cd "/Users/sandeepnarayan/projects/agents/Whatsapp Summarizer"

# Load API key from parent .env file
export OPENAI_API_KEY=$(grep OPENAI_API_KEY ../.env | cut -d '=' -f2)

# Start the app
python3 app_prod.py
```

Then open: http://localhost:8000

### Stop the Server

Press `Ctrl+C` in the terminal, or:
```bash
lsof -ti:8000 | xargs kill -9
```

## Update WhatsApp Chat

When you get new chat exports:

```bash
# 1. Place _chat.txt in "WhatsApp Chat/" folder

# 2. Load API key
export OPENAI_API_KEY=$(grep OPENAI_API_KEY ../.env | cut -d '=' -f2)

# 3. Recreate vector database
python3 whatsappvector.py

# 4. Restart the app
python3 app_prod.py
```

## Cost

- **Vector DB creation**: ~$0.02 (only when chat updates)
- **Per conversation**: ~$0.001
- **Monthly (100 queries/day)**: ~$3-5

## Files

- `app_prod.py` - Production server (run this)
- `whatsappvector.py` - Update vector DB (run when chat updates)
- `VectorDB/` - Vector database (created by script)
- `WhatsApp Chat/_chat.txt` - Source chat data

## Troubleshooting

**Can't access http://localhost:8000**
```bash
# Check if server is running
curl http://localhost:8000/health

# If not, start it:
python3 app_prod.py
```

**"Vector database not found"**
```bash
# Create it first:
python3 whatsappvector.py
```

**Responses seem generic**
- The vector DB might be empty
- Re-run: `python3 whatsappvector.py`

## Support Documentation

- **PRODUCTION_SETUP.md** - Detailed setup guide
- **IMPLEMENTATION_SUMMARY.md** - Architecture overview
- **README.md** - Project overview

---

**Current Server**: Running successfully ✅
**Vector DB Items**: 170 chunks
**Ready to use**: YES! Open http://localhost:8000
