"""LLM 客户端：封装外部大模型 API（OpenAI 兼容协议）的流式生成。"""

import json
from collections.abc import AsyncIterator
from dataclasses import dataclass, field

import httpx

from app.core.config import settings


@dataclass
class StreamResult:
    """流式生成结果，包含文本增量迭代器与 Token 统计。"""

    chunks: AsyncIterator[str]
    usage: dict = field(default_factory=dict)

    def __aiter__(self):
        return self.chunks.__aiter__()

    def __anext__(self):
        return self.chunks.__anext__()


class LLMClient:
    """大模型 API 客户端（OpenAI 兼容协议）。"""

    def stream_chat(
        self, messages: list[dict], model: str | None = None
    ) -> StreamResult:
        """流式生成回答，返回可迭代的文本增量 + Token 统计。

        用法：
            result = llm_client.stream_chat(messages)
            async for chunk in result:
                ...
            tokens = result.usage  # {"prompt_tokens": x, "completion_tokens": y, "total_tokens": z}
        """
        if not settings.llm_api_url or not settings.llm_api_key:
            return StreamResult(chunks=self._fallback_stream(messages))

        url = settings.llm_api_url.rstrip("/") + "/chat/completions"
        headers = {
            "Authorization": f"Bearer {settings.llm_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": model or settings.llm_model,
            "messages": messages,
            "stream": True,
            "stream_options": {"include_usage": True},
        }

        usage: dict = {}

        async def gen() -> AsyncIterator[str]:
            nonlocal usage
            async with httpx.AsyncClient(timeout=60) as client:
                async with client.stream(
                    "POST", url, json=payload, headers=headers
                ) as resp:
                    resp.raise_for_status()
                    async for line in resp.aiter_lines():
                        if not line.startswith("data:"):
                            continue
                        data = line[5:].strip()
                        if data == "[DONE]":
                            break
                        try:
                            obj = json.loads(data)
                        except ValueError:
                            continue
                        # 解析 token 用量（OpenAI 流式末尾的 usage chunk）
                        if obj.get("usage"):
                            usage = {
                                "prompt_tokens": obj["usage"].get("prompt_tokens", 0),
                                "completion_tokens": obj["usage"].get(
                                    "completion_tokens", 0
                                ),
                                "total_tokens": obj["usage"].get("total_tokens", 0),
                            }
                        try:
                            delta = obj["choices"][0]["delta"].get("content")
                            if delta:
                                yield delta
                        except (KeyError, IndexError):
                            continue

        return StreamResult(chunks=gen(), usage=usage)

    async def _fallback_stream(self, messages: list[dict]) -> AsyncIterator[str]:
        """未配置 LLM API 时的占位回答流。"""
        question = ""
        for m in messages:
            if m.get("role") == "user":
                question = m.get("content", "")
        answer = f"[占位回答] 当前未配置 LLM API，无法生成真实回答。你的问题是：{question}"
        yield answer


llm_client = LLMClient()
