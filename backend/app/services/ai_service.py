"""AI 鉴权检索服务：登录校验 → 召回 → 鉴权 → 拼装 → 流式生成。

本阶段采用简化召回实现（关键词/最近更新单元），后续替换为 LangGraph 检索工作流。
"""

import asyncio
import json
import time
import uuid

from sqlalchemy import or_, select
from sqlalchemy.ext.asyncio import AsyncSession

from app.models import KnowledgeUnit, User
from app.services.llm_client import llm_client
from app.services.log_service import log_service
from app.services.permission_engine import permission_engine


class AiService:
    """AI 鉴权问答服务。"""

    async def chat(
        self,
        db: AsyncSession,
        user: User,
        question: str,
        session_id: str | None = None,
    ) -> dict:
        """执行一轮问答，返回（召回、鉴权结果、回答生成器）。

        返回结构：
        {
            "session_id": str,
            "recalled": list[int],
            "authorized": list[int],
            "unauthorized": list[int],
            "answer_stream": 异步生成器，逐段 yield 文本
        }
        """
        session_id = session_id or uuid.uuid4().hex
        t0 = time.time()

        # 1. 简化召回：关键词匹配 + 最近更新单元
        recalled = await self._retrieve(db, question)

        # 2. 数据权限鉴权
        authorized, unauthorized = await permission_engine.check_units(
            db, user.id, [u.id for u in recalled]
        )

        # 3. 组装授权内容上下文
        authorized_units = [u for u in recalled if u.id in authorized]
        context = self._build_context(authorized_units)

        # 4. 生成回答（流式）
        prompt_messages = self._build_messages(question, context)

        async def answer_stream():
            parts: list[str] = []
            async for chunk in llm_client.stream_chat(prompt_messages):
                parts.append(chunk)
                yield chunk
            # 5. 权限缺失提示
            if unauthorized:
                hint = self._build_unauthorized_hint(unauthorized)
                yield hint
            # 6. 异步记录日志
            answer = "".join(parts)
            asyncio.create_task(
                log_service.record(
                    session_id=session_id,
                    user_id=user.id,
                    question=question,
                    answer=answer,
                    recalled_unit_ids=[u.id for u in recalled],
                    authorized_unit_ids=authorized,
                    unauthorized_unit_ids=unauthorized,
                    response_time_ms=int((time.time() - t0) * 1000),
                )
            )

        return {
            "session_id": session_id,
            "recalled": [u.id for u in recalled],
            "authorized": authorized,
            "unauthorized": unauthorized,
            "answer_stream": answer_stream(),
        }

    async def _retrieve(self, db: AsyncSession, question: str) -> list[KnowledgeUnit]:
        """简化召回：关键词匹配已发布单元，不足则补充最近更新单元。"""
        # 提取关键词（简单按空格/标点切分，取长度 >= 2 的词）
        import re

        keywords = [w for w in re.split(r"[\s,，。！？!?、]+", question) if len(w) >= 2]

        query = select(KnowledgeUnit).where(KnowledgeUnit.status == "published")
        if keywords:
            conds = []
            for kw in keywords[:5]:
                conds.append(KnowledgeUnit.title.ilike(f"%{kw}%"))
                conds.append(KnowledgeUnit.content.ilike(f"%{kw}%"))
            query = query.where(or_(*conds))

        result = await db.execute(query.order_by(KnowledgeUnit.updated_at.desc()).limit(10))
        return list(result.scalars().all())

    def _build_context(self, units: list[KnowledgeUnit]) -> str:
        """拼装授权知识单元内容作为上下文。"""
        if not units:
            return "（无可用知识内容）"
        parts = []
        for u in units:
            parts.append(f"【{u.title}】\n{u.summary or u.content[:500]}")
        return "\n\n".join(parts)

    def _build_messages(self, question: str, context: str) -> list[dict]:
        """组装 LLM 消息。"""
        system = (
            "你是知识库问答助手。请仅根据提供的知识内容回答用户问题，"
            "不要编造知识内容以外的信息。若知识内容不足以回答，请如实说明。"
        )
        return [
            {"role": "system", "content": system},
            {"role": "user", "content": f"知识内容：\n{context}\n\n用户问题：{question}"},
        ]

    def _build_unauthorized_hint(self, unauthorized_ids: list[int]) -> str:
        """生成权限缺失提示。"""
        ids = "、".join(str(i) for i in unauthorized_ids)
        return (
            f"\n\n⚠️ 提示：检索结果中部分知识单元（ID：{ids}）"
            "您暂无访问权限，相关内容未纳入本次回答。"
        )


ai_service = AiService()
