"""AI 问答接口。"""

import json

from fastapi import APIRouter, Depends, Query
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.services.ai_service import ai_service
from app.services.session_service import session_service

router = APIRouter(prefix="/ai", tags=["AI 问答"])


class ChatRequest(BaseModel):
    question: str = Field(..., description="提问内容")
    session_id: str | None = Field(None, description="会话 ID，为空则新建")


def _sse(event_type: str, data: dict) -> str:
    """构造 SSE 事件。"""
    return f"event: {event_type}\ndata: {json.dumps(data, ensure_ascii=False)}\n\n"


@router.post("/chat/stream")
async def chat_stream(
    req: ChatRequest,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """SSE 流式问答（强制登录态 + 数据权限鉴权）。"""

    result = await ai_service.chat(db, user, req.question, req.session_id)

    async def gen():
        # 先发送元信息（召回/授权/未授权/是否兜底）
        yield _sse(
            "meta",
            {
                "session_id": result["session_id"],
                "recalled": result["recalled"],
                "authorized": result["authorized"],
                "unauthorized": result["unauthorized"],
                "used_fallback": result["used_fallback"],
            },
        )
        # 逐 token 流式发送回答增量
        async for chunk in result["answer_stream"]:
            yield _sse("delta", {"content": chunk})
        yield _sse("done", {})

    return StreamingResponse(gen(), media_type="text/event-stream")


@router.get("/sessions")
async def list_sessions(
    page: int = Query(1, ge=1),
    page_size: int = Query(20, ge=1, le=100),
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询当前用户的会话列表。"""
    return await session_service.list_sessions(db, user.id, page, page_size)


@router.get("/sessions/{session_id}/messages")
async def get_session_messages(
    session_id: str,
    db: AsyncSession = Depends(get_db),
    user: User = Depends(get_current_user),
):
    """查询某会话的历史消息。"""
    return await session_service.get_messages(db, session_id, user.id)
