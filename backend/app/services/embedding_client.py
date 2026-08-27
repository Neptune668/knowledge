"""Embedding 客户端：调用外部向量化 API（OpenAI 调用方式）。"""

import httpx

from app.core.config import settings


class EmbeddingClient:
    """向量化 API 客户端（OpenAI 兼容 /embeddings 接口）。"""

    async def embed(self, text: str) -> list[float]:
        """单条文本向量化，返回指定维度向量。"""
        result = await self.embed_batch([text])
        return result[0]

    async def embed_batch(self, texts: list[str]) -> list[list[float]]:
        """批量向量化。

        :param texts: 文本列表
        :return: 向量列表，每个向量维度为 settings.embedding_dim
        """
        if not texts:
            return []
        if not settings.embedding_api_url:
            return self._fallback_embed(texts)

        url = settings.embedding_api_url.rstrip("/") + "/embeddings"
        headers = {
            "Authorization": f"Bearer {settings.embedding_api_key}",
            "Content-Type": "application/json",
        }
        payload = {
            "model": settings.embedding_model,
            "input": texts,
        }

        async with httpx.AsyncClient(timeout=60) as client:
            resp = await client.post(url, json=payload, headers=headers)
            resp.raise_for_status()
            data = resp.json()

        # OpenAI 兼容：data[i].embedding
        embeddings = [item["embedding"] for item in data["data"]]
        return embeddings

    def _fallback_embed(self, texts: list[str]) -> list[list[float]]:
        """未配置 embedding API 时返回占位向量（保证流程可跑通）。

        占位向量为固定维度，仅用于开发调试，不参与真实检索。
        """
        dim = settings.embedding_dim
        return [[0.0] * dim for _ in texts]


embedding_client = EmbeddingClient()
