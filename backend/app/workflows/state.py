"""LangGraph 工作流共享状态定义。"""

from typing import Annotated, Literal, TypedDict

from langgraph.graph.message import add_messages


class IngestionState(TypedDict, total=False):
    """知识导入工作流状态。"""

    task_id: str
    files: list            # [{filename, text}]
    parsed_docs: list      # [{filename, text}]
    chunks: list           # [{unit_id, chunk_index, content, token_count}]
    embeddings: list       # [[float, ...]]
    unit_ids: list         # 入库后的知识单元 ID
    errors: list           # 各文件错误信息


class RetrievalState(TypedDict, total=False):
    """检索问答工作流状态（M8 使用）。"""

    question: str
    session_id: str
    user_id: int
    messages: Annotated[list, add_messages]
    recalled_units: list
    recalled_chunks: list
    top_score: float
    authorized_units: list
    unauthorized_units: list
    context: str
    answer: str
    prompt_messages: list      # 待发送给 LLM 的消息（generate/fallback 产出）
    used_fallback: bool
    retry_count: int
    route: Literal["faq_cache", "retrieve", "rewrite", "fallback", "generate"]
