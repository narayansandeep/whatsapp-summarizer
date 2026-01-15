"""
WhatsApp Running Coach Chat Application - Flask Production Version
Uses OpenAI API with Pinecone cloud vector database
Optimized for Vercel serverless deployment
"""

from flask import Flask, request, jsonify, send_from_directory
from flask_cors import CORS
from typing import List, Dict
import uuid
from datetime import datetime, timedelta
import os
from pinecone import Pinecone
from openai import OpenAI
from dotenv import load_dotenv

# Load environment variables from .env file
load_dotenv()

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")
PINECONE_INDEX_NAME = "whatsapp-chat"

app = Flask(__name__, static_folder='static')
CORS(app)

# Initialize OpenAI client
client = OpenAI()

# Initialize Pinecone client (will be loaded on first use)
pinecone_index = None

# Session storage: {session_id: {"history": [...], "last_access": datetime}}
sessions = {}

def get_vector_db():
    """Initialize and return the Pinecone index."""
    global pinecone_index

    if pinecone_index is not None:
        return pinecone_index

    pinecone_api_key = os.getenv('PINECONE_API_KEY')
    if not pinecone_api_key:
        raise Exception(
            "PINECONE_API_KEY not found in environment variables. "
            "Please add it to your .env file or Vercel environment variables."
        )

    try:
        pc = Pinecone(api_key=pinecone_api_key)
        pinecone_index = pc.Index(PINECONE_INDEX_NAME)
        print(f"✅ Connected to Pinecone index: {PINECONE_INDEX_NAME}")
        return pinecone_index
    except Exception as e:
        raise Exception(
            f"Failed to connect to Pinecone index '{PINECONE_INDEX_NAME}'. "
            f"Please ensure the index exists and your API key is correct. Error: {e}"
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
    index = get_vector_db()

    # Generate embedding for the query
    response = client.embeddings.create(
        input=query,
        model="text-embedding-3-small"
    )
    query_embedding = response.data[0].embedding

    # Search in Pinecone
    results = index.query(
        vector=query_embedding,
        top_k=n_results,
        include_metadata=True
    )

    # Extract and return the documents from metadata
    documents = []
    if results and results.get('matches'):
        for match in results['matches']:
            if 'metadata' in match and 'text' in match['metadata']:
                documents.append(match['metadata']['text'])

    return documents

def get_ai_response(user_message: str, conversation_history: List[Dict]) -> str:
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
        "content": f"""You are a helpful AI assistant that answers questions STRICTLY based on the WhatsApp group chat provided below.

WHATSAPP CHAT CONTEXT:
{context_str}

CRITICAL INSTRUCTIONS - YOU MUST FOLLOW THESE EXACTLY:
1. ONLY use information that is explicitly mentioned in the WhatsApp chat context above
2. DO NOT add any information from your general knowledge about running, training, or anything else
3. DO NOT provide advice that is not directly mentioned in the chat messages
4. If the WhatsApp chat context does not contain relevant information to answer the question, you MUST respond with: "I don't have information about that in the WhatsApp chat history. Please ask about topics that have been discussed in the group."
5. When answering, quote or paraphrase what was actually said in the chat messages
6. Be helpful and friendly, but stay strictly within the boundaries of the chat context provided

Remember: Your ONLY source of information is the WhatsApp chat context above. Do not use any other knowledge.
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

@app.route('/')
def read_root():
    """Serve the main HTML page"""
    try:
        html_path = os.path.join(STATIC_DIR, "index.html")
        if not os.path.exists(html_path):
            return jsonify({"error": f"HTML file not found at {html_path}"}), 500

        with open(html_path, "r") as f:
            return f.read()
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/chat', methods=['POST'])
def chat():
    """Handle chat requests"""
    try:
        cleanup_old_sessions()

        # Get request data
        data = request.get_json()
        user_message = data.get('message')
        session_id = data.get('session_id') or str(uuid.uuid4())

        if not user_message:
            return jsonify({"error": "Message is required"}), 400

        # Get or create session
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
        user_msg = {
            "role": "user",
            "message": user_message,
            "timestamp": datetime.now().isoformat()
        }
        conversation_history.append(user_msg)

        # Get AI response
        response_text = get_ai_response(user_message, conversation_history)

        # Add assistant response to history
        assistant_msg = {
            "role": "assistant",
            "message": response_text,
            "timestamp": datetime.now().isoformat()
        }
        conversation_history.append(assistant_msg)

        # Store updated history back to session
        sessions[session_id]["history"] = conversation_history

        return jsonify({
            "response": response_text,
            "session_id": session_id
        })

    except Exception as e:
        print(f"Error in chat endpoint: {e}")
        return jsonify({"error": f"Error processing request: {str(e)}"}), 500

@app.route('/reset', methods=['POST'])
def reset_session():
    """Reset a session's conversation history"""
    try:
        data = request.get_json()
        session_id = data.get('session_id')

        if session_id and session_id in sessions:
            sessions[session_id]["history"] = []
            sessions[session_id]["last_access"] = datetime.now()

        return jsonify({"status": "success", "message": "Session reset"})
    except Exception as e:
        return jsonify({"error": str(e)}), 500

@app.route('/health')
def health_check():
    """Health check endpoint"""
    try:
        # Try to access vector DB to ensure it's available
        index = get_vector_db()
        vector_db_status = "available"

        # Get index stats
        stats = index.describe_index_stats()
        item_count = stats.get('total_vector_count', 0)
    except Exception as e:
        vector_db_status = f"unavailable: {str(e)}"
        item_count = 0

    return jsonify({
        "status": "healthy",
        "sessions": len(sessions),
        "vector_db": vector_db_status,
        "vector_db_items": item_count
    })

# For local development
if __name__ == "__main__":
    print("="*60)
    print("WhatsApp Running Coach - Flask Production Server")
    print("="*60)
    print("Starting server on http://localhost:5000")
    print("="*60)
    app.run(host="0.0.0.0", port=5000, debug=True)
