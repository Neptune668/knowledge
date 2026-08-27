"""检索问答工作流节点：faq_cache / retrieve / authorize / rewrite / generate / fallback。"""

from app.core.config import settings
from app.core.database import async_session_factory
from app.models import KnowledgeUnit
from app.services.embedding_client import embedding_client
from app.services.llm_client import llm_client
from app.services.milvus_service import milvus_service
from app.services.permission_engine import permission_engine
from app.workflows.state import RetrievalState


async def faq_cache_node(state: RetrievalState) -> RetrievalState:
    """FAQ 缓存命中判断。"""
    from app.services.faq_cache_service import faq_cache_service

    answer = await faq_cache_service.match(state["question"])
    if answer:
        state["answer"] = answer
        state["used_fallback"] = False
    return state


async def retrieve_node(state: RetrievalState) -> RetrievalState:
    """混合召回：Milvus 向量检索 + PostgreSQL 关键字检索。"""
    question = state["question"]
    recalled_chunks: list[dict] = []
    top_score = 0.0

    # 1. 向量检索
    try:
        query_vec = await embedding_client.embed(question)
        hits = milvus_service.search(query_vec, top_k=settings.recall_top_k)
        for h in hits:
            recalled_chunks.append(h)
            score = h.get("distance", 0.0)
            if score > top_score:
                top_score = score
    except Exception:  # noqa: BLE001 向量检索失败降级为关键字
        pass

    # 2. 关键字检索（PostgreSQL，仅当向量结果不足时补充）
    if len(recalled_chunks) < settings.recall_top_k:
        keyword_chunks = await _keyword_search(question, settings.recall_top_k)
        existing = {c.get("chunk_id") for c in recalled_chunks}
        for kc in keyword_chunks:
            if kc["chunk_id"] not in existing:
                recalled_chunks.append(kc)

    state["recalled_chunks"] = recalled_chunks
    state["top_score"] = top_score
    return state


async def authorize_node(state: RetrievalState) -> RetrievalState:
    """权限鉴权：按 unit_id 拆分授权/未授权。"""
    recalled_chunks = state.get("recalled_chunks", [])
    unit_ids = list({c["unit_id"] for c in recalled_chunks if c.get("unit_id")})

    authorized_ids, unauthorized_ids = await _check_units(state["user_id"], unit_ids)

    state["authorized_units"] = authorized_ids
    state["unauthorized_units"] = unauthorized_ids
    return state


async def rewrite_node(state: RetrievalState) -> RetrievalState:
    """问题改写：召回不足时改写问题重试。"""
    question = state["question"]
    # 用 LLM 改写（简化：加提示词让 LLM 生成改写问题）
    messages = [
        {
            "role": "system",
            "content": "你是检索问题改写助手。请将用户问题改写为更利于知识检索的表述，只输出改写后的问题。",
        },
        {"role": "user", "content": question},
    ]
    rewritten = ""
    async for chunk in llm_client.stream_chat(messages):
        rewritten += chunk
    state["question"] = rewritten.strip() or question
    state["retry_count"] = state.get("retry_count", 0) + 1
    return state


async def generate_node(state: RetrievalState) -> RetrievalState:
    """生成回答：基于授权知识组装 Context 后 LLM 生成。"""
    # 组装授权知识内容
    authorized_units = state.get("authorized_units", [])
    context = await _build_context(authorized_units)
    state["context"] = context

    prompt_messages = [
        {
            "role": "system",
            "content": "你是知识库问答助手。请仅根据提供的知识内容回答，不要编造知识内容以外的信息。",
        },
        {
            "role": "user",
            "content": f"知识内容：\n{context}\n\n用户问题：{state['question']}",
        },
    ]
    answer = ""
    async for chunk in llm_client.stream_chat(prompt_messages):
        answer += chunk
    state["answer"] = answer
    state["used_fallback"] = False
    return state


async def fallback_node(state: RetrievalState) -> RetrievalState:
    """模型兜底：检索不足时用 LLM 通用能力回答。"""
    prompt_messages = [
        {
            "role": "system",
            "content": (
                "你是通用问答助手。用户的问题未在知识库中检索到相关内容，"
                "请基于你的通用知识直接回答，并在开头说明「以下回答未基于知识库内容」。"
            ),
        },
        {"role": "user", "content": state["question"]},
    ]
    answer = ""
    async for chunk in llm_client.stream_chat(prompt_messages):
        answer += chunk
    state["answer"] = answer
    state["used_fallback"] = True
    return state


# ===== 内部辅助 =====


async def _keyword_search(question: str, top_k: int) -> list[dict]:
    """PostgreSQL 关键字检索（按标题/正文模糊匹配）。"""
    import re

    from sqlalchemy import or_, select

    keywords = [w for w in re.split(r"[\s,，。！？!?、]+", question) if len(w) >= 2]
    if not keywords:
        return []

    query = select(KnowledgeUnit.id).where(KnowledgeUnit.status == "published")
    conds = []
    for kw in keywords[:5]:
        conds.append(KnowledgeUnit.title.ilike(f"%{kw}%"))
        conds.append(KnowledgeUnit.content.ilike(f"%{kw}%"))
    query = query.where(or_(*conds)).limit(top_k)

    async with async_session_factory() as db:
        result = await db.execute(query)
        unit_ids = [row[0] for row in result.all()]
        chunks = []
        for uid in unit_ids:
            unit = await db.get(KnowledgeUnit, uid)
            if unit:
                chunks.append(
                    {
                        "chunk_id": None,
                        "unit_id": uid,
                        "content": unit.summary or unit.content[:200],
                        "distance": 0.0,
                    }
                )
        return chunks


async def _check_units(user_id: int, unit_ids: list[int]) -> tuple[list[int], list[int]]:
    """调用权限引擎鉴权。"""
    async with async_session_factory() as db:
        return await permission_engine.check_units(db, user_id, unit_ids)


async def _build_context(unit_ids: list[int]) -> str:
    """拼装授权知识单元内容。"""
    if not unit_ids:
        return "（无可用知识内容）"
    from sqlalchemy import select

    async with async_session_factory() as db:
        result = await db.execute(
            select(KnowledgeUnit).where(KnowledgeUnit.id.in_(unit_ids))
        )
        units = result.scalars().all()
        parts = []
        for u in units:
            parts.append(f"【{u.title}】\n{u.summary or u.content[:500]}")
        return "\n\n".join(parts)
