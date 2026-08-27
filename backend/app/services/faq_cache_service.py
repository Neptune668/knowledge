"""FAQ 缓存服务：审核通过的 FAQ 写入 Redis，提供精确/语义相似度匹配。"""

import json

from redis.asyncio import Redis

from app.core.config import settings

FAQ_EXACT_PREFIX = "faq:exact:"
FAQ_VECTOR_PREFIX = "faq:vec:"


def _cosine(a: list[float], b: list[float]) -> float:
    """计算两个向量的余弦相似度。"""
    if not a or not b or len(a) != len(b):
        return 0.0
    dot = sum(x * y for x, y in zip(a, b))
    norm_a = sum(x * x for x in a) ** 0.5
    norm_b = sum(x * x for x in b) ** 0.5
    if norm_a == 0 or norm_b == 0:
        return 0.0
    return dot / (norm_a * norm_b)


class FaqCacheService:
    """FAQ 问答缓存。"""

    def __init__(self) -> None:
        self._redis: Redis | None = None

    async def _get_redis(self) -> Redis | None:
        """惰性获取 Redis 连接（Redis 未启动时返回 None 降级）。"""
        if self._redis is None:
            try:
                self._redis = Redis.from_url(settings.redis_url, decode_responses=True)
                await self._redis.ping()
            except Exception:
                self._redis = None
        return self._redis

    async def set_faq(self, question: str, answer: str) -> None:
        """将 FAQ 写入精确匹配缓存，并预计算问题向量（供语义匹配）。"""
        r = await self._get_redis()
        if r is None:
            return
        await r.set(FAQ_EXACT_PREFIX + question, answer)
        # 预计算问题向量，加速语义匹配
        try:
            from app.services.embedding_client import embedding_client

            vec = await embedding_client.embed(question)
            await r.set(FAQ_VECTOR_PREFIX + question, json.dumps(vec))
        except Exception:
            pass

    async def delete_faq(self, question: str) -> None:
        """删除 FAQ 缓存。"""
        r = await self._get_redis()
        if r is None:
            return
        await r.delete(FAQ_EXACT_PREFIX + question)
        await r.delete(FAQ_VECTOR_PREFIX + question)

    async def match(self, question: str) -> str | None:
        """匹配提问：先精确匹配，再语义相似度匹配。"""
        r = await self._get_redis()
        if r is None:
            return None

        # 1. 精确匹配
        exact = await r.get(FAQ_EXACT_PREFIX + question)
        if exact:
            return exact

        # 2. 语义相似度匹配
        return await self._semantic_match(question, r)

    async def _semantic_match(self, question: str, r: Redis) -> str | None:
        """语义匹配：对提问向量化，与已缓存 FAQ 问题向量比对。"""
        from app.services.embedding_client import embedding_client

        # 收集所有 FAQ 问题及其向量
        keys = []
        async for key in r.scan_iter(match=FAQ_VECTOR_PREFIX + "*"):
            keys.append(key)
        if not keys:
            return None

        try:
            query_vec = await embedding_client.embed(question)
        except Exception:
            return None

        best_question: str | None = None
        best_score: float = 0.0
        for key in keys:
            raw = await r.get(key)
            if not raw:
                continue
            try:
                vec = json.loads(raw)
            except (ValueError, TypeError):
                continue
            score = _cosine(query_vec, vec)
            if score > best_score:
                best_score = score
                best_question = key[len(FAQ_VECTOR_PREFIX):]

        if best_question and best_score >= settings.faq_sim_threshold:
            return await r.get(FAQ_EXACT_PREFIX + best_question)
        return None


faq_cache_service = FaqCacheService()
