"""LLM 客户端：封装外部大模型 API（OpenAI 兼容协议）的流式生成。"""

from collections.abc import AsyncIterator

import httpx

from app.core.config import settings


class LLMClient:
    """大模型 API 客户端（OpenAI 兼容协议）。"""

    async def stream_chat(
        self, messages: list[dict], model: str | None = None
    ) -> AsyncIterator[str]:
        """流式生成回答，逐段 yield 文本增量。

        当未配置 LLM API 时，返回占位回答，保证鉴权闭环可独立验证。
        """
        if not settings.llm_api_url or not settings.llm_api_key:
            async for chunk in self._fallback_stream(messages):
                yield chunk
            return

        url = settings.llm_api_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or settings.llm_model,
            "messages": messages,
            "stream": True,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            async with client.stream("POST", url, json=payload, headers=headers) as resp:
                resp.raise_for_status()
                async for line in resp.aiter_lines():
                    if not line.startswith("data:"):
                        continue
                    data = line[5:].strip()
                    if data == "[DONE]":
                        break
                    try:
                        import json

                        obj = json.loads(data)
                        delta = obj["choices"][0]["delta"].get("content")
                        if delta:
                            yield delta
                    except (KeyError, IndexError, ValueError):
                        continue

    async def _fallback_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """未配置 LLM API 时的占位回答流。"""
        question = ""
        for m in messages:
            if m.get("role") == "user":
                question = m.get("content", "")
        answer = f"[占位回答] 当前未配置 LLM API，无法生成真实回答。你的问题是：{question}"
        yield answer


llm_client = LLMClient()
