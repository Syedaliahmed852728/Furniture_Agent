from utils import Assistant, create_tool_node_with_fallback
from typing import Annotated
from langgraph.graph.message import AnyMessage, add_messages
from typing_extensions import TypedDict
from langgraph.graph import END, START, StateGraph
from tools_and_primary_agent import Primary_agent, get_primary_agent_tools, route_primary_assistant
from langchain_core.messages import AIMessage, HumanMessage, ToolMessage

from dotenv import load_dotenv
import json

load_dotenv()

class State(TypedDict):
    messages: Annotated[list[AnyMessage], add_messages]


def build_graph():
    builder = StateGraph(State)
    builder.add_node("primary_agent", Assistant(Primary_agent))
    builder.add_node("primary_agent_tools", create_tool_node_with_fallback(get_primary_agent_tools()))
    builder.add_edge("primary_agent_tools", "primary_agent")
    builder.add_conditional_edges(
        "primary_agent",
        route_primary_assistant,
        {
            "primary_agent_tools": "primary_agent_tools",
            "end": END,
        },
    )
    builder.add_edge(START, "primary_agent")

    return builder.compile()


def get_sql_query_from_tool_calls(response):
    messages = response.get("messages", [])
    for message in reversed(messages):
        if isinstance(message, AIMessage):
            tool_calls = message.additional_kwargs.get("tool_calls", [])
            for tool_call in tool_calls:
                if tool_call.get("function", {}).get("name") == "run_sql_query":
                    raw_args = tool_call.get("function", {}).get("arguments", "")
                    try:
                        args = json.loads(raw_args) 
                        return args.get("query", "")  
                    except json.JSONDecodeError:
                        return ""  # if invalid JSON
    return ""

def get_sql_and_human_readable_output(question):
    graph = build_graph()
    messages = [HumanMessage(content=question)]
    response = graph.invoke({"messages": messages})
    sql_query = get_sql_query_from_tool_calls(response=response)
    # print("response is:- ", response)
    ai_messages = [
        msg for msg in response["messages"] if isinstance(msg, AIMessage)
    ]
    last_ai_message = (
        ai_messages[-1].content if ai_messages else "No response generated"
    )
    # print(last_ai_message)
    return sql_query, last_ai_message