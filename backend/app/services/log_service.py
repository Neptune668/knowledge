"""问答访问日志服务：异步记录每轮问答的访问日志。"""

from datetime import datetime, timezone

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.database import async_session_factory
from app.models import QaAccessLog


class LogService:
    """问答访问日志。"""

    async def record(
        self,
        session_id: str,
        user_id: int | None,
        question: str,
        answer: str | None,
        recalled_unit_ids: list[int],
        authorized_unit_ids: list[int],
        unauthorized_unit_ids: list[int],
        prompt_tokens: int = 0,
        completion_tokens: int = 0,
        total_tokens: int = 0,
        response_time_ms: int = 0,
    ) -> None:
        """异步写入一条访问日志（独立会话，不阻塞主流程）。"""
        async with async_session_factory() as db:
            log = QaAccessLog(
                session_id=session_id,
                user_id=user_id,
                question=question,
                answer=answer,
                recalled_unit_ids_json=recalled_unit_ids,
                authorized_unit_ids_json=authorized_unit_ids,
                unauthorized_unit_ids_json=unauthorized_unit_ids,
                prompt_tokens=prompt_tokens,
                completion_tokens=completion_tokens,
                total_tokens=total_tokens,
                response_time_ms=response_time_ms,
                created_at=datetime.now(timezone.utc),
            )
            db.add(log)
            await db.commit()


log_service = LogService()
