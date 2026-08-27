"""AI 鉴权检索服务：登录校验 → 检索工作流（LangGraph）→ 流式回答 → 日志落库。

M8：使用 retrieval_graph 工作流（Milvus 混合召回 + 权限鉴权 + 模型兜底）。
"""

import asyncio
import time
import uuid

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.services.log_service import log_service
from app.workflows.retrieval_graph import retrieval_graph


class AiService:
    """AI 鉴权问答服务。"""

    async def chat(
        self,
        db: AsyncSession,
        user: User,
        question: str,
        session_id: str | None = None,
    ) -> dict:
        """执行一轮问答，返回（召回、鉴权结果、回答）。

        返回结构：
        {
            "session_id": str,
            "recalled": list[int],
            "authorized": list[int],
            "unauthorized": list[int],
            "used_fallback": bool,
            "answer": str,
        }
        """
        session_id = session_id or uuid.uuid4().hex
        t0 = time.time()

        # 注入工作流初始状态并执行（invoke 拿到最终状态）
        init_state = {
            "question": question,
            "session_id": session_id,
            "user_id": user.id,
            "messages": [("user", question)],
            "retry_count": 0,
        }
        result = await retrieval_graph.ainvoke(init_state)

        answer = result.get("answer", "")
        recalled_chunks = result.get("recalled_chunks", [])
        recalled = list({c["unit_id"] for c in recalled_chunks if c.get("unit_id")})
        authorized = result.get("authorized_units", [])
        unauthorized = result.get("unauthorized_units", [])
        used_fallback = result.get("used_fallback", False)

        # 权限缺失提示
        if unauthorized:
            answer += self._build_unauthorized_hint(unauthorized)

        # 异步记录日志
        asyncio.create_task(
            log_service.record(
                session_id=session_id,
                user_id=user.id,
                question=question,
                answer=answer,
                recalled_unit_ids=recalled,
                authorized_unit_ids=authorized,
                unauthorized_unit_ids=unauthorized,
                response_time_ms=int((time.time() - t0) * 1000),
            )
        )

        return {
            "session_id": session_id,
            "recalled": recalled,
            "authorized": authorized,
            "unauthorized": unauthorized,
            "used_fallback": used_fallback,
            "answer": answer,
        }

    def _build_unauthorized_hint(self, unauthorized_ids: list[int]) -> str:
        """生成权限缺失提示。"""
        ids = "、".join(str(i) for i in unauthorized_ids)
        return (
            f"\n\n⚠️ 提示：检索结果中部分知识单元（ID：{ids}）"
            "您暂无访问权限，相关内容未纳入本次回答。"
        )


ai_service = AiService()
