from utils import Assistant, create_tool_node_with_fallback
from typing import Annotated
from langgraph.graph.message import AnyMessage, add_messages
from typing_extensions import TypedDict
from langgraph.checkpoint.memory import MemorySaver
from langgraph.graph import END, START, StateGraph
from tools_and_primary_agent import Primary_agent, get_primary_agent_tools, route_primary_assistant

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

    memory = MemorySaver()
    return builder.compile(checkpointer=memory)
