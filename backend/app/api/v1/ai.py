"""AI 问答接口。"""

import json

from fastapi import APIRouter, Depends
from fastapi.responses import StreamingResponse
from pydantic import BaseModel, Field
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import get_db
from app.core.deps import get_current_user
from app.models import User
from app.services.ai_service import ai_service

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
        # 发送完整回答（M8 当前为一次性返回，后续可优化为 token 级流式）
        yield _sse("delta", {"content": result["answer"]})
        yield _sse("done", {})

    return StreamingResponse(gen(), media_type="text/event-stream")
