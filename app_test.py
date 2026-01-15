"""
Simple test version of the app that mocks the agents library
to verify the web app structure works correctly
"""
from fastapi import FastAPI, HTTPException
from fastapi.responses import HTMLResponse
from pydantic import BaseModel
from typing import Optional
import uuid
from datetime import datetime, timedelta
import asyncio
import os

# Get the directory where this script is located
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
STATIC_DIR = os.path.join(BASE_DIR, "static")

app = FastAPI()

# Session storage: {session_id: {"history": [...], "last_access": datetime}}
sessions = {}

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
        # Mock response - in reality this would call the agents
        # Simulate processing time
        await asyncio.sleep(0.5)

        # Generate mock response based on keywords
        message_lower = request.message.lower()
        if any(word in message_lower for word in ["injury", "recover", "recovery", "hurt"]):
            response_text = "Based on the running group's WhatsApp chat, here's advice about injury recovery:\n\n1. **Stop and Assess**: Apply the RICE principle (Rest, Ice, Compression, Elevation)\n2. **Seek Medical Attention**: Consult a professional for proper diagnosis\n3. **Modify Training**: Work with your coach to adjust your training plan\n4. **Gradual Return**: Follow a phased approach back to full training\n5. **Focus on Nutrition and Sleep**: Support recovery with proper nutrition\n\nThis is a TEST RESPONSE. Install the 'agents' library for actual functionality."
        elif any(word in message_lower for word in ["marathon", "race", "event", "run"]):
            response_text = "For marathon training, the running group suggests:\n\n- Build your base mileage gradually\n- Include long runs on weekends\n- Practice race pace runs\n- Don't forget strength training\n- Stay consistent with your training plan\n\nThis is a TEST RESPONSE. Install the 'agents' library for actual functionality."
        elif any(word in message_lower for word in ["diet", "nutrition", "food", "eat"]):
            response_text = "Nutrition advice from the running group:\n\n- Eat a balanced diet with adequate protein\n- Stay hydrated throughout the day\n- Time your meals around your runs\n- Consider carb-loading before long runs\n- Don't skip post-run recovery nutrition\n\nThis is a TEST RESPONSE. Install the 'agents' library for actual functionality."
        else:
            response_text = f"Hello! I'm your running coach assistant. I can help you with questions about training, recovery, nutrition, and running events. You asked: '{request.message}'\n\nThis is a TEST RESPONSE. Install the 'agents' library for actual functionality."

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
        raise HTTPException(status_code=500, detail=f"Error processing request: {str(e)}")

class ResetRequest(BaseModel):
    session_id: str

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
    return {"status": "healthy", "sessions": len(sessions)}

if __name__ == "__main__":
    import uvicorn
    print("Starting test server on http://localhost:8000")
    print("This is a TEST version with mock responses.")
    print("Install the 'agents' library for full functionality.")
    uvicorn.run(app, host="0.0.0.0", port=8000)
