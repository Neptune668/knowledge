"""知识导入工作流（M7）：parse → split → embed → persist。"""

from langgraph.graph import END, StateGraph

from app.workflows.nodes.ingestion_nodes import (
    embed_node,
    parse_node,
    persist_node,
    split_node,
)
from app.workflows.state import IngestionState


def build_ingestion_graph():
    """构建知识导入工作流图。"""
    graph = StateGraph(IngestionState)

    graph.add_node("parse", parse_node)
    graph.add_node("split", split_node)
    graph.add_node("embed", embed_node)
    graph.add_node("persist", persist_node)

    graph.set_entry_point("parse")
    graph.add_edge("parse", "split")
    graph.add_edge("split", "embed")
    graph.add_edge("embed", "persist")
    graph.add_edge("persist", END)

    return graph.compile()


ingestion_graph = build_ingestion_graph()
