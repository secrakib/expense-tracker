from backend.src.agent.V3 import build_graph

graph = build_graph()
print(graph.get_graph().draw_mermaid())