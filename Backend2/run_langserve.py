import uuid
from typing import AsyncIterator

import uvicorn
from fastapi import FastAPI, Request
from langchain_core.messages import AIMessage, HumanMessage
from langchain_core.runnables import RunnableConfig, RunnableLambda
from langserve import add_routes
from main import build_graph
from pydantic import BaseModel, Field
from dotenv import load_dotenv

load_dotenv()

app = FastAPI(
    title="Multi-Agent Chat Assistant",
    version="1.0",
    description="API with conversation memory and agent routing",
)


# 1. Define input schema with thread_id
class ChatInput(BaseModel):
    user_query: str = Field(..., description="The user's input message")
    thread_id: str = Field(
        default_factory=lambda: str(uuid.uuid4()),
        description="Unique conversation ID",
    )


# 2. Store the compiled graph in app state
@app.on_event("startup")
def compile_graph():
    app.state.graph = build_graph()


# 3. Adapter to handle input conversion
async def process_input(input_dict: dict) -> AsyncIterator[AIMessage]:
    # Parse input using Pydantic model
    input_data = ChatInput(**input_dict)
    messages = [HumanMessage(content=input_data.user_query)]
    # Initialize state with thread_id
    config = {"configurable": {"thread_id": input_data.thread_id}}
    initial_state = {
        "messages": messages,
        # "dialog_state": [],
        # "config": config,
    }

    # Process through the graph
    final_state = await app.state.graph.ainvoke(initial_state, config=config)
    ai_messages = [
        msg for msg in final_state["messages"] if isinstance(msg, AIMessage)
    ]
    last_ai_message = (
        ai_messages[-1].content if ai_messages else "No response generated"
    )
    return last_ai_message


# 4. Configure thread_id handling
async def thread_config_modifier(request: Request, config: RunnableConfig):
    try:
        body = await request.json()
        thread_id = body.get("thread_id", str(uuid.uuid4()))
    except:
        thread_id = str(uuid.uuid4())
    return {"configurable": {"thread_id": thread_id}}


# 5. Add routes with proper configuration
add_routes(
    app,
    RunnableLambda(process_input).with_types(
        input_type=ChatInput,
        output_type=str,
    ),
    path="/assistant",
    playground_type="default",  # Changed to chat
    # config_keys=["configurable"],
    # per_req_config_modifier=thread_config_modifier,
    enable_feedback_endpoint=True,
    enable_public_trace_link_endpoint=True,
    disabled_endpoints=["batch"],
)


if __name__ == "__main__":
    uvicorn.run(
        "run_langserve:app", host="localhost", port=8000, reload=True, workers=1
    )
