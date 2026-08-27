"""AI 鉴权检索服务：登录校验 → 检索工作流（LangGraph）→ 流式回答 → 日志落库。

M8：使用 retrieval_graph 工作流（Milvus 混合召回 + 权限鉴权 + 模型兜底）。
P0 优化：真正的 token 级流式输出 + Token 用量统计。
"""

import asyncio
import time
import uuid
from collections.abc import AsyncIterator

from sqlalchemy.ext.asyncio import AsyncSession

from app.models import User
from app.services.llm_client import llm_client
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
        """执行一轮问答，返回（召回/鉴权元信息 + 流式回答生成器）。

        返回结构：
        {
            "session_id": str,
            "recalled": list[int],
            "authorized": list[int],
            "unauthorized": list[int],
            "used_fallback": bool,
            "answer_stream": 异步生成器（逐 token yield 文本）
        }
        """
        session_id = session_id or uuid.uuid4().hex
        t0 = time.time()

        # 0. 获取历史对话上下文（多轮对话）
        from app.services.session_service import session_service

        history = await session_service.get_history_messages(
            db, session_id, user.id
        )

        # 1. 执行检索工作流（决策：知识问答 or 模型兜底 or FAQ 命中）
        init_state = {
            "question": question,
            "session_id": session_id,
            "user_id": user.id,
            "messages": [("user", question)],
            "history": history,
            "retry_count": 0,
        }
        result = await retrieval_graph.ainvoke(init_state)

        # 2. 提取工作流决策结果
        recalled_chunks = result.get("recalled_chunks", [])
        recalled = list({c["unit_id"] for c in recalled_chunks if c.get("unit_id")})
        authorized = result.get("authorized_units", [])
        unauthorized = result.get("unauthorized_units", [])
        used_fallback = result.get("used_fallback", False)
        cached_answer = result.get("answer", "")  # FAQ 命中时的缓存答案
        prompt_messages = result.get("prompt_messages", [])

        # 3. 构造流式回答生成器
        async def answer_stream() -> AsyncIterator[str]:
            usage: dict = {}
            answer_parts: list[str] = []

            if cached_answer:
                # FAQ 缓存命中，直接返回标准答案
                answer_parts.append(cached_answer)
                yield cached_answer
            elif prompt_messages:
                # 真实流式生成（注入多轮对话历史）
                final_messages = self._inject_history(prompt_messages, history)
                stream_result = llm_client.stream_chat(final_messages)
                async for chunk in stream_result:
                    answer_parts.append(chunk)
                    yield chunk
                usage = stream_result.usage

            # 权限缺失提示
            if unauthorized:
                hint = self._build_unauthorized_hint(unauthorized)
                answer_parts.append(hint)
                yield hint

            # 4. 异步记录日志（含 token 统计）
            answer = "".join(answer_parts)
            asyncio.create_task(
                log_service.record(
                    session_id=session_id,
                    user_id=user.id,
                    question=question,
                    answer=answer,
                    recalled_unit_ids=recalled,
                    authorized_unit_ids=authorized,
                    unauthorized_unit_ids=unauthorized,
                    prompt_tokens=usage.get("prompt_tokens", 0),
                    completion_tokens=usage.get("completion_tokens", 0),
                    total_tokens=usage.get("total_tokens", 0),
                    response_time_ms=int((time.time() - t0) * 1000),
                )
            )

        return {
            "session_id": session_id,
            "recalled": recalled,
            "authorized": authorized,
            "unauthorized": unauthorized,
            "used_fallback": used_fallback,
            "answer_stream": answer_stream(),
        }

    def _build_unauthorized_hint(self, unauthorized_ids: list[int]) -> str:
        """生成权限缺失提示。"""
        ids = "、".join(str(i) for i in unauthorized_ids)
        return (
            f"\n\n⚠️ 提示：检索结果中部分知识单元（ID：{ids}）"
            "您暂无访问权限，相关内容未纳入本次回答。"
        )

    @staticmethod
    def _inject_history(prompt_messages: list[dict], history: list[dict]) -> list[dict]:
        """将多轮对话历史注入到 LLM 消息中（system 在最前，历史在中间，当前提问在最后）。"""
        if not history:
            return prompt_messages

        # prompt_messages 结构：[system, user(当前提问)]
        system = prompt_messages[0] if prompt_messages else None
        current_user = prompt_messages[-1] if prompt_messages else None

        # 过滤历史中与当前提问重复的内容
        history = [h for h in history if h.get("content") != current_user.get("content")]

        result = []
        if system:
            result.append(system)
        result.extend(history)
        if current_user and current_user is not system:
            result.append(current_user)
        return result


ai_service = AiService()
