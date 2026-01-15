"""
WhatsApp Running Coach Chat Application - Production Version
Uses OpenAI API directly with local ChromaDB vector database
"""

from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional, List, Dict
import uuid
from datetime import datetime, timedelta
import asyncio
import os
import chromadb
from chromadb.config import Settings
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
VECTOR_DB_FOLDER = "VectorDB"
COLLECTION_NAME = "whatsapp_running_chat"

app = FastAPI()

# Initialize OpenAI client
client = OpenAI()

# Initialize ChromaDB client (will be loaded on first use)
chroma_client = None
collection = None

# Session storage: {session_id: {"history": [...], "last_access": datetime}}
sessions = {}

def get_vector_db():
    """Initialize and return the ChromaDB collection."""
    global chroma_client, collection

    if collection is not None:
        return collection

    vector_db_path = os.path.join(BASE_DIR, VECTOR_DB_FOLDER)

    if not os.path.exists(vector_db_path):
        raise Exception(
            f"Vector database not found at {vector_db_path}. "
            "Please run 'python3 whatsappvector.py' first to create the database."
        )

    chroma_client = chromadb.PersistentClient(
        path=vector_db_path,
        settings=Settings(anonymized_telemetry=False)
    )

    try:
        collection = chroma_client.get_collection(name=COLLECTION_NAME)
        print(f"✅ Loaded vector database: {COLLECTION_NAME}")
        return collection
    except Exception as e:
        raise Exception(
            f"Failed to load collection '{COLLECTION_NAME}'. "
            f"Please run 'python3 whatsappvector.py' first. Error: {e}"
        )

def search_whatsapp_context(query: str, n_results: int = 5) -> List[str]:
    """
    Search the WhatsApp chat vector database for relevant context.

    Args:
        query: The user's question
        n_results: Number of relevant chunks to retrieve

    Returns:
        List of relevant chat excerpts
    """
    collection = get_vector_db()

    # Generate embedding for the query
    response = client.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    )
    query_embedding = response.data[0].embedding

    # Search in ChromaDB
    results = collection.query(
        query_embeddings=[query_embedding],
        n_results=n_results
    )

    # Extract and return the documents
    if results and results['documents']:
        return results['documents'][0]  # Returns list of matching documents
    return []

async def get_ai_response(user_message: str, conversation_history: List[Dict]) -> str:
    """
    Get AI response using OpenAI API with context from WhatsApp chat vector database.

    Args:
        user_message: The user's current question
        conversation_history: Previous conversation messages

    Returns:
        AI assistant's response
    """
    # Search for relevant context from WhatsApp chat
    relevant_context = search_whatsapp_context(user_message, n_results=5)

    # Build context string
    context_str = "\n\n---\n\n".join(relevant_context) if relevant_context else "No relevant context found."

    # Build messages for OpenAI
    system_message = {
        "role": "system",
        "content": f"""You are a helpful AI running coach assistant. You help runners with training advice,
recovery tips, nutrition guidance, and information about running events.

You have access to a WhatsApp group chat from a running training group. Use this context to answer questions:

WHATSAPP CHAT CONTEXT:
{context_str}

Instructions:
1. Answer based on the WhatsApp chat context as much as possible
2. If the question is about training, recovery, or nutrition, refer to advice from the chat
3. If asking about events, you can search the web or provide general guidance, but keep it brief
4. Be concise, helpful, and friendly
5. If you don't have relevant information, say so politely
"""
    }

    # Build conversation messages
    messages = [system_message]

    # Add conversation history (last 10 messages for context)
    for msg in conversation_history[-10:]:
        role = msg.get("role", "user")
        if role == "user":
            messages.append({
                "role": "user",
                "content": msg.get("message", msg.get("content", [{}])[0].get("text", ""))
            })
        elif role == "assistant":
            messages.append({
                "role": "assistant",
                "content": msg.get("message", "")
            })

    # Call OpenAI API
    try:
        response = client.chat.completions.create(
            model="gpt-4o-mini",
            messages=messages,
            temperature=0.7,
            max_tokens=800
        )

        return response.choices[0].message.content

    except Exception as e:
        print(f"Error calling OpenAI API: {e}")
        return f"I apologize, but I encountered an error processing your request. Please try again."

# Clean up old sessions (older than 1 hour)
def cleanup_old_sessions():
    current_time = datetime.now()
    expired_sessions = [
        sid for sid, data in sessions.items()
        if current_time - data["last_access"] > timedelta(hours=1)
    ]
    for sid in expired_sessions:
        del sessions[sid]

class ChatRequest(BaseModel):
    message: str
    session_id: Optional[str] = None

class ChatResponse(BaseModel):
    response: str
    session_id: str

class ResetRequest(BaseModel):
    session_id: str

@app.get("/", response_class=HTMLResponse)
async def read_root():
    html_path = os.path.join(STATIC_DIR, "index.html")
    if not os.path.exists(html_path):
        raise HTTPException(status_code=500, detail=f"HTML file not found at {html_path}")
    with open(html_path, "r") as f:
        return f.read()

@app.post("/chat", response_model=ChatResponse)
async def chat(request: ChatRequest):
    cleanup_old_sessions()

    # Get or create session
    session_id = request.session_id or str(uuid.uuid4())

    if session_id not in sessions:
        sessions[session_id] = {
            "history": [],
            "last_access": datetime.now()
        }

    # Update last access time
    sessions[session_id]["last_access"] = datetime.now()

    # Get conversation history
    conversation_history = sessions[session_id]["history"]

    # Add user message to history
    user_message = {
        "role": "user",
        "message": request.message,
        "timestamp": datetime.now().isoformat()
    }
    conversation_history.append(user_message)

    try:
        # Get AI response
        response_text = await get_ai_response(request.message, conversation_history)

        # Add assistant response to history
        assistant_message = {
            "role": "assistant",
            "message": response_text,
            "timestamp": datetime.now().isoformat()
        }
        conversation_history.append(assistant_message)

        # Store updated history back to session
        sessions[session_id]["history"] = conversation_history

        return ChatResponse(
            response=response_text,
            session_id=session_id
        )

    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

@app.post("/reset")
async def reset_session(request: ResetRequest):
    """Reset a session's conversation history"""
    if request.session_id in sessions:
        sessions[request.session_id]["history"] = []
        sessions[request.session_id]["last_access"] = datetime.now()
    return {"status": "success", "message": "Session reset"}

@app.get("/health")
async def health_check():
    """Health check endpoint"""
    try:
        # Try to access vector DB to ensure it's available
        collection = get_vector_db()
        vector_db_status = "available"
        item_count = collection.count()
    except Exception as e:
        vector_db_status = f"unavailable: {str(e)}"
        item_count = 0

    return {
        "status": "healthy",
        "sessions": len(sessions),
        "vector_db": vector_db_status,
        "vector_db_items": item_count
    }

if __name__ == "__main__":
    import uvicorn
    print("="*60)
    print("WhatsApp Running Coach - Production Server")
    print("="*60)
    print(f"Vector DB: {os.path.join(BASE_DIR, VECTOR_DB_FOLDER)}")
    print("Starting server on http://localhost:8000")
    print("="*60)
    uvicorn.run(app, host="0.0.0.0", port=8000)
