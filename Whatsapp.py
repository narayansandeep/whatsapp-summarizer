from agents import FileSearchTool, WebSearchTool, Agent, ModelSettings, TResponseInputItem, Runner, RunConfig
from pydantic import BaseModel
import asyncio

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


class WorkflowInput(BaseModel):
  input_as_text: str


# Main code entrypoint
async def run_workflow(workflow_input: WorkflowInput):
  state = {

  }
  workflow = workflow_input.model_dump()
  conversation_history: list[TResponseInputItem] = [
    {
      "role": "user",
      "content": [
        {
          "type": "input_text",
          "text": workflow["input_as_text"]
        }
      ]
    }
  ]
  greeting_result_temp = await Runner.run(
    greeting,
    input=[
      *conversation_history
    ],
    run_config=RunConfig(trace_metadata={
      "__trace_source__": "agent-builder",
      "workflow_id": "wf_68e4efaf64ac8190936826ade60fd3910d7efe675e39fbd9"
    })
  )

  conversation_history.extend([item.to_input_item() for item in greeting_result_temp.new_items])

  greeting_result = {
    "output_text": greeting_result_temp.final_output.json(),
    "output_parsed": greeting_result_temp.final_output.model_dump()
  }
  
  # Initialize result variables
  training_info_result = None
  event_name_result = None
  agent_result = None
  
  if greeting_result["output_parsed"]["training_goal"] != "":
    training_info_result_temp = await Runner.run(
      training_info,
      input=[
        *conversation_history
      ],
      run_config=RunConfig(trace_metadata={
        "__trace_source__": "agent-builder",
        "workflow_id": "wf_68e4efaf64ac8190936826ade60fd3910d7efe675e39fbd9"
      })
    )

    conversation_history.extend([item.to_input_item() for item in training_info_result_temp.new_items])

    training_info_result = {
      "output_text": training_info_result_temp.final_output_as(str)
    }
    return training_info_result
    
  elif greeting_result["output_parsed"]["event_info"] != "":
    event_name_result_temp = await Runner.run(
      event_name,
      input=[
        *conversation_history
      ],
      run_config=RunConfig(trace_metadata={
        "__trace_source__": "agent-builder",
        "workflow_id": "wf_68e4efaf64ac8190936826ade60fd3910d7efe675e39fbd9"
      })
    )

    conversation_history.extend([item.to_input_item() for item in event_name_result_temp.new_items])

    event_name_result = {
      "output_text": event_name_result_temp.final_output_as(str)
    }
    return event_name_result
    
  else:
    agent_result_temp = await Runner.run(
      agent,
      input=[
        *conversation_history
      ],
      run_config=RunConfig(trace_metadata={
        "__trace_source__": "agent-builder",
        "workflow_id": "wf_68e4efaf64ac8190936826ade60fd3910d7efe675e39fbd9"
      })
    )

    conversation_history.extend([item.to_input_item() for item in agent_result_temp.new_items])

    agent_result = {
      "output_text": agent_result_temp.final_output_as(str)
    }
    return agent_result

# Example usage - run the coroutine and print the output
if __name__ == "__main__":
    # Create a sample input
    sample_input = WorkflowInput(input_as_text="Hello, I'm training for a marathon. Can you help me with my training plan?")
    
    # Run the coroutine and print the output
    result = asyncio.run(run_workflow(sample_input))
    print("Workflow result:", result)
