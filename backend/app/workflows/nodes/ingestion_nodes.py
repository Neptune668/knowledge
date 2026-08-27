"""知识导入工作流节点：parse / split / embed / persist。"""

import uuid

from app.core.database import async_session_factory
from app.models import KnowledgeChunk, KnowledgeUnit
from app.services.embedding_client import embedding_client
from app.services.milvus_service import milvus_service
from app.utils.parser import parse_content
from app.utils.text_splitter import estimate_tokens, split_text
from app.workflows.state import IngestionState


async def parse_node(state: IngestionState) -> IngestionState:
    """解析文档为纯文本。"""
    parsed_docs = []
    errors = state.get("errors", [])
    for f in state.get("files", []):
        try:
            text = parse_content(f["filename"], f["raw"])
            parsed_docs.append({"filename": f["filename"], "text": text})
        except Exception as e:  # noqa: BLE001
            errors.append({"filename": f["filename"], "error": str(e)})
    state["parsed_docs"] = parsed_docs
    state["errors"] = errors
    return state


async def split_node(state: IngestionState) -> IngestionState:
    """文本切片。"""
    chunks = []
    for doc in state.get("parsed_docs", []):
        pieces = split_text(doc["text"])
        for idx, piece in enumerate(pieces):
            chunks.append(
                {
                    "filename": doc["filename"],
                    "chunk_index": idx,
                    "content": piece,
                    "token_count": estimate_tokens(piece),
                }
            )
    state["chunks"] = chunks
    return state


async def embed_node(state: IngestionState) -> IngestionState:
    """向量化所有切片。"""
    chunks = state.get("chunks", [])
    if not chunks:
        state["embeddings"] = []
        return state
    texts = [c["content"] for c in chunks]
    state["embeddings"] = await embedding_client.embed_batch(texts)
    return state


async def persist_node(state: IngestionState) -> IngestionState:
    """写 PostgreSQL（unit + chunk）+ Milvus（向量）。"""
    chunks = state.get("chunks", [])
    embeddings = state.get("embeddings", [])
    unit_ids: list[int] = []

    if not chunks:
        state["unit_ids"] = []
        return state

    # 按文件分组，每个文件一个知识单元
    from collections import defaultdict

    grouped: dict[str, list] = defaultdict(list)
    for i, c in enumerate(chunks):
        grouped[c["filename"]].append((i, c))

    async with async_session_factory() as db:
        for filename, items in grouped.items():
            # 1. 创建知识单元
            title = filename.rsplit(".", 1)[0] if "." in filename else filename
            full_text = "\n\n".join(chunks[i]["content"] for i, _ in items)
            unit = KnowledgeUnit(
                unit_code="KU-" + uuid.uuid4().hex[:12].upper(),
                title=title,
                content=full_text,
                summary=full_text[:200],
                source_file_name=filename,
                file_type=filename.rsplit(".", 1)[-1].lower() if "." in filename else "",
                status="draft",
            )
            db.add(unit)
            await db.flush()
            unit_ids.append(unit.id)

            # 2. 创建切片记录 + 组装 Milvus 行（保持 chunk_id 顺序映射）
            milvus_rows = []
            chunk_objs = []
            for idx, c in items:
                chunk = KnowledgeChunk(
                    unit_id=unit.id,
                    chunk_index=c["chunk_index"],
                    content=c["content"],
                    token_count=c["token_count"],
                )
                db.add(chunk)
                await db.flush()
                chunk_objs.append(chunk)
                milvus_rows.append(
                    {
                        "chunk_id": chunk.id,
                        "unit_id": unit.id,
                        "content": c["content"],
                        "dense_vector": embeddings[idx],
                    }
                )

            # 3. 写入 Milvus，回填 milvus_id（按插入顺序对应）
            try:
                milvus_ids = milvus_service.insert(milvus_rows)
                for i, chunk in enumerate(chunk_objs):
                    if i < len(milvus_ids):
                        chunk.milvus_id = milvus_ids[i]
            except Exception as e:  # noqa: BLE001
                # Milvus 写入失败不阻断 PG 入库，记录到 errors
                state.setdefault("errors", []).append(
                    {"filename": filename, "error": f"Milvus 写入失败: {e}"}
                )

        await db.commit()

    state["unit_ids"] = unit_ids
    return state
