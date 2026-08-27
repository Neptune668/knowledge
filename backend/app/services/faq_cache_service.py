"""FAQ 缓存服务：审核通过的 FAQ 写入 Redis，提供精确/语义匹配。"""

import json

from redis.asyncio import Redis

from app.core.config import settings

FAQ_EXACT_PREFIX = "faq:exact:"


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
        """将 FAQ 写入精确匹配缓存。"""
        r = await self._get_redis()
        if r is not None:
            await r.set(FAQ_EXACT_PREFIX + question, answer)

    async def delete_faq(self, question: str) -> None:
        """删除 FAQ 缓存。"""
        r = await self._get_redis()
        if r is not None:
            await r.delete(FAQ_EXACT_PREFIX + question)

    async def match(self, question: str) -> str | None:
        """精确匹配提问（本阶段语义匹配后续接入向量能力）。"""
        r = await self._get_redis()
        if r is None:
            return None
        return await r.get(FAQ_EXACT_PREFIX + question)


faq_cache_service = FaqCacheService()
