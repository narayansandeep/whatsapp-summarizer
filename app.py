from fastapi import FastAPI, HTTPException
from fastapi.staticfiles import StaticFiles
from fastapi.responses import HTMLResponse, JSONResponse
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
        "content": [
            {
                "type": "input_text",
                "text": request.message
            }
        ]
    }
    conversation_history.append(user_message)

    try:
        # Run workflow with the accumulated conversation history
        result = await run_workflow_with_history(request.message, conversation_history)

        # Store updated history back to session
        sessions[session_id]["history"] = conversation_history

        response_text = result.get("output_text", "I apologize, I couldn't process your request.")

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

async def run_workflow_with_history(message: str, conversation_history: list):
    """
    Modified version of run_workflow that uses existing conversation history
    """
    from agents import Agent, ModelSettings, Runner, RunConfig, FileSearchTool, WebSearchTool
    from pydantic import BaseModel

    # Tool definitions
    file_search = FileSearchTool(
        vector_store_ids=[
            "vs_68e665b3074c8191b6655dc14c46dca0"
        ]
    )
    web_search_preview = WebSearchTool(
        search_context_size="medium",
        user_location={
            "type": "approximate"
        }
    )

    class GreetingSchema(BaseModel):
        training_goal: str
        event_info: str

    greeting = Agent(
        name="Greeting",
        instructions="""You are an AI assistant running coach. First you will greet the runner, and ask for any query.

Look through the conversation to extract the following:
1. Training goal(is there a question related to any aspect related to training)
2. Target Event (a query related to a running event)

If the above details are present anywhere in the conversation, return:
{
  \"training goal\": <user-provided goal>,
  \"event info\": \"<Running Event name>\",
 }""",
        model="gpt-4.1-mini",
        output_type=GreetingSchema,
        model_settings=ModelSettings(
            temperature=1,
            top_p=1,
            max_tokens=2048,
            store=True
        )
    )

    training_info = Agent(
        name="Training Info",
        instructions="Refer to the attached WhatsApp chat of a running group to answer questions",
        model="gpt-4.1-mini",
        tools=[
            file_search
        ],
        model_settings=ModelSettings(
            temperature=1,
            top_p=1,
            max_tokens=2048,
            store=True
        )
    )

    event_name = Agent(
        name="Event Name",
        instructions="Search for the requested information regarding the event from the internet and provide the answer",
        model="gpt-4.1-mini",
        tools=[
            web_search_preview
        ],
        model_settings=ModelSettings(
            temperature=1,
            top_p=1,
            max_tokens=2048,
            store=True
        )
    )

    agent = Agent(
        name="Agent",
        instructions="Courteously reply that you don't know the answer to the query",
        model="gpt-4o-mini",
        model_settings=ModelSettings(
            temperature=1,
            top_p=1,
            max_tokens=2048,
            store=True
        )
    )

    # Run greeting agent with full conversation history
    greeting_result_temp = await Runner.run(
        greeting,
        input=conversation_history,
        run_config=RunConfig(trace_metadata={
            "__trace_source__": "agent-builder",
            "workflow_id": "wf_68e4efaf64ac8190936826ade60fd3910d7efe675e39fbd9"
        })
    )

    # Add greeting agent's response to history
    conversation_history.extend([item.to_input_item() for item in greeting_result_temp.new_items])

    greeting_result = {
        "output_text": greeting_result_temp.final_output.model_dump_json(),
        "output_parsed": greeting_result_temp.final_output.model_dump()
    }

    # Route to appropriate agent based on intent
    if greeting_result["output_parsed"]["training_goal"] != "":
        training_info_result_temp = await Runner.run(
            training_info,
            input=conversation_history,
            run_config=RunConfig(trace_metadata={
                "__trace_source__": "agent-builder",
                "workflow_id": "wf_68e4efaf64ac8190936826ade60fd3910d7efe675e39fbd9"
            })
        )

        conversation_history.extend([item.to_input_item() for item in training_info_result_temp.new_items])

        return {
            "output_text": training_info_result_temp.final_output_as(str)
        }

    elif greeting_result["output_parsed"]["event_info"] != "":  # Fixed bug from original code
        event_name_result_temp = await Runner.run(
            event_name,
            input=conversation_history,
            run_config=RunConfig(trace_metadata={
                "__trace_source__": "agent-builder",
                "workflow_id": "wf_68e4efaf64ac8190936826ade60fd3910d7efe675e39fbd9"
            })
        )

        conversation_history.extend([item.to_input_item() for item in event_name_result_temp.new_items])

        return {
            "output_text": event_name_result_temp.final_output_as(str)
        }

    else:
        agent_result_temp = await Runner.run(
            agent,
            input=conversation_history,
            run_config=RunConfig(trace_metadata={
                "__trace_source__": "agent-builder",
                "workflow_id": "wf_68e4efaf64ac8190936826ade60fd3910d7efe675e39fbd9"
            })
        )

        conversation_history.extend([item.to_input_item() for item in agent_result_temp.new_items])

        return {
            "output_text": agent_result_temp.final_output_as(str)
        }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run(app, host="0.0.0.0", port=8000)
