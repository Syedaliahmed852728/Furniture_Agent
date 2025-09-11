from langchain_core.runnables import Runnable, RunnableConfig, RunnableLambda
from langgraph.prebuilt import ToolNode
from langchain_core.messages import ToolMessage
from langchain_openai import ChatOpenAI
import os
from dotenv import load_dotenv

load_dotenv()

openia_api_key =os.getenv("OPENAI_API_KEY")

class Assistant:
    def __init__(self, runnable: Runnable):
        self.runnable = runnable

    def __call__(self, state, config: RunnableConfig):
        while True:
            result = self.runnable.invoke(state)

            if not result.tool_calls and (
                not result.content
                or isinstance(result.content, list)
                and not result.content[0].get("text")
            ):
                messages = state["messages"] + [
                    ("user", "Respond with a real output.")
                ]
                state = {**state, "messages": messages}
            else:
                break
        return {"messages": result}
    
def handle_tool_error(state) -> dict:
    error = state.get("error")
    tool_calls = state["messages"][-1].tool_calls
    return {
        "messages": [
            ToolMessage(
                content=f"Error: {repr(error)}\n Tell the customer an error occured and escalate back to the main assistant.",
                tool_call_id=tc["id"],
            )
            for tc in tool_calls
        ]
    }

def create_tool_node_with_fallback(tools: list) -> dict:
    return ToolNode(tools).with_fallbacks(
        [RunnableLambda(handle_tool_error)], exception_key="error"
    )


llm_agent = ChatOpenAI(model='gpt-4o',
                       temperature=0,
                       max_tokens = None,
                       timeout=None,
                       max_retries=2,
                       api_key=openia_api_key)