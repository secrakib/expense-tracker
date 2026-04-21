from langgraph.graph import StateGraph, END
from typing import TypedDict

# Define your state
class AgentState(TypedDict):
    messages: list
    intent: str

# Import your node
from backend.src.agent.V1 import intent_router_node

# Create graph
builder = StateGraph(AgentState)

builder.add_node("intent_router", intent_router_node)

# Simple flow
builder.set_entry_point("intent_router")
builder.add_edge("intent_router", END)

graph = builder.compile()

state = {
    "messages": [
        {"role": "user", "content": "Hello"}
    ]
}
config = {"configurable": {"thread_id": "1"}}
result = graph.invoke(state)
print(result)


result = graph.invoke(
    {
        "messages": [
            {"role": "user", "content": "I spent 200 on food"}
        ]
    },
    config=config
)

print(result)