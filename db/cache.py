"""
Distributed Caching and State Coordination.
Interfaces with Redis with automatic fallback to high-performance local memory store.
"""

import asyncio
from datetime import datetime, timezone
from typing import Any

from core.config import get_settings
from core.logger import get_agent_logger

logger = get_agent_logger("db.cache")


class DistributedCache:
    """
    Caching interface supporting Redis cluster/standalone with transparent memory fallback.
    """

    def __init__(self) -> None:
        self.settings = get_settings()
        self._redis = None
        self._in_memory: dict[str, tuple[Any, float]] = {}
        self._lock = asyncio.Lock()
        self._initialized = False

    async def _init_redis(self) -> None:
        if self._initialized:
            return
        self._initialized = True
        redis_url = self.settings.REDIS_URL
        if redis_url:
            try:
                import redis.asyncio as aioredis
                client = aioredis.from_url(redis_url, decode_responses=True)
                await client.ping()
                self._redis = client
                logger.info(f"Connected to Redis cache at {redis_url}")
            except Exception as exc:
                logger.warning(f"Redis at {redis_url} not reachable ({exc}). Using in-memory cache.")
                self._redis = None

    async def get(self, key: str) -> Any | None:
        """Retrieve value by key."""
        await self._init_redis()
        if self._redis:
            try:
                return await self._redis.get(key)
            except Exception as exc:
                logger.warning(f"Redis get error: {exc}. Reading from memory cache.")

        async with self._lock:
            if key in self._in_memory:
                val, expires_at = self._in_memory[key]
                if datetime.now(timezone.utc).timestamp() < expires_at:
                    return val
                else:
                    del self._in_memory[key]
            return None

    async def set(self, key: str, value: Any, ttl_seconds: int = 3600) -> None:
        """Store value with expiration."""
        await self._init_redis()
        if self._redis:
            try:
                await self._redis.set(key, str(value), ex=ttl_seconds)
                return
            except Exception as exc:
                logger.warning(f"Redis set error: {exc}. Storing in memory cache.")

        async with self._lock:
            expires_at = datetime.now(timezone.utc).timestamp() + ttl_seconds
            self._in_memory[key] = (value, expires_at)

    async def exists(self, key: str) -> bool:
        """Check if key exists and is unexpired."""
        val = await self.get(key)
        return val is not None

    async def delete(self, key: str) -> None:
        """Remove key from cache."""
        await self._init_redis()
        if self._redis:
            try:
                await self._redis.delete(key)
            except Exception as exc:
                logger.warning(f"Redis delete error: {exc}")

        async with self._lock:
            self._in_memory.pop(key, None)


# Global cache instance
cache_service = DistributedCache()
