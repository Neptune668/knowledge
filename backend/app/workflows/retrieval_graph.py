"""检索问答工作流（M8）：faq_cache → retrieve → authorize → 路由 → generate/fallback。"""

from langgraph.graph import END, StateGraph

from app.core.config import settings
from app.workflows.nodes.retrieval_nodes import (
    authorize_node,
    fallback_node,
    faq_cache_node,
    generate_node,
    retrieve_node,
    rewrite_node,
)
from app.workflows.state import RetrievalState


def route_after_faq_cache(state: RetrievalState) -> str:
    """FAQ 命中直接生成，未命中走检索。"""
    if state.get("answer"):
        return "generate"
    return "retrieve"


def route_after_authorize(state: RetrievalState) -> str:
    """鉴权后路由：无授权知识→兜底；相似度不足→改写重试或兜底；充分→生成。"""
    if not state.get("authorized_units"):
        return "fallback"

    top_score = state.get("top_score", 0.0)
    if top_score < settings.retrieve_min_score:
        if state.get("retry_count", 0) < settings.max_retry:
            return "rewrite"
        return "fallback"

    return "generate"


def build_retrieval_graph():
    """构建检索问答工作流图。"""
    graph = StateGraph(RetrievalState)

    graph.add_node("faq_cache", faq_cache_node)
    graph.add_node("retrieve", retrieve_node)
    graph.add_node("authorize", authorize_node)
    graph.add_node("rewrite", rewrite_node)
    graph.add_node("generate", generate_node)
    graph.add_node("fallback", fallback_node)

    graph.set_entry_point("faq_cache")

    graph.add_conditional_edges(
        "faq_cache",
        route_after_faq_cache,
        {"retrieve": "retrieve", "generate": "generate"},
    )
    graph.add_edge("retrieve", "authorize")
    graph.add_conditional_edges(
        "authorize",
        route_after_authorize,
        {"generate": "generate", "rewrite": "rewrite", "fallback": "fallback"},
    )
    graph.add_edge("rewrite", "retrieve")
    graph.add_edge("generate", END)
    graph.add_edge("fallback", END)

    return graph.compile()


retrieval_graph = build_retrieval_graph()
