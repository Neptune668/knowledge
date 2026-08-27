"""问答会话管理服务：会话列表、历史消息、多轮对话上下文。"""

from sqlalchemy import distinct, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import QaAccessLog


class SessionService:
    """会话管理业务逻辑。"""

    async def list_sessions(
        self, db: AsyncSession, user_id: int, page: int = 1, page_size: int = 20
    ) -> dict:
        """查询用户的会话列表（按会话最新时间倒序）。"""
        # 每个 session_id 取最新一条日志时间
        subq = (
            select(
                QaAccessLog.session_id,
                func.max(QaAccessLog.created_at).label("last_time"),
            )
            .where(QaAccessLog.user_id == user_id)
            .group_by(QaAccessLog.session_id)
            .subquery()
        )
        count_result = await db.execute(
            select(func.count()).select_from(subq)
        )
        total = count_result.scalar_one()

        result = await db.execute(
            select(subq.c.session_id, subq.c.last_time)
            .order_by(subq.c.last_time.desc())
            .offset((page - 1) * page_size)
            .limit(page_size)
        )
        items = [
            {"session_id": row[0], "last_time": row[1].isoformat() if row[1] else None}
            for row in result.all()
        ]
        return {"total": total, "items": items}

    async def get_messages(
        self, db: AsyncSession, session_id: str, user_id: int | None = None
    ) -> list[dict]:
        """查询某会话的历史消息（按时间正序）。"""
        query = select(QaAccessLog).where(QaAccessLog.session_id == session_id)
        if user_id is not None:
            query = query.where(QaAccessLog.user_id == user_id)
        result = await db.execute(query.order_by(QaAccessLog.created_at.asc()))
        logs = result.scalars().all()
        messages: list[dict] = []
        for log in logs:
            messages.append(
                {
                    "role": "user",
                    "content": log.question,
                    "created_at": log.created_at.isoformat() if log.created_at else None,
                }
            )
            if log.answer:
                messages.append(
                    {
                        "role": "assistant",
                        "content": log.answer,
                        "created_at": log.created_at.isoformat() if log.created_at else None,
                    }
                )
        return messages

    async def get_history_messages(
        self, db: AsyncSession, session_id: str, user_id: int, limit: int = 10
    ) -> list[dict]:
        """获取多轮对话上下文（最近 N 条，供 LLM 使用）。"""
        messages = await self.get_messages(db, session_id, user_id)
        # 取最近 limit 条（一轮 = 一问一答 2 条）
        return messages[-limit * 2:]


session_service = SessionService()
