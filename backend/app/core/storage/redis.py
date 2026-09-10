import pickle
from typing import Any

from redis.asyncio import ConnectionPool, Redis

from app.core.config import logger


class RedisCache:
    def __init__(self, redis_url: str):
        self.redis_url = redis_url
        self.redis: Redis | None = None
        self.pool: ConnectionPool | None = None

    async def connect(self) -> None:
        if self.redis:
            try:
                if await self.redis.ping():
                    return
            except Exception as e:
                logger.debug("Redis ping failed, reconnecting: %s", type(e).__name__)

        try:
            if self.redis:
                await self.redis.close()
            if self.pool:
                await self.pool.disconnect(inuse_connections=True)

            self.pool = ConnectionPool.from_url(
                self.redis_url,
                max_connections=20,
                decode_responses=False,
            )
            self.redis = Redis(connection_pool=self.pool)
            await self.redis.ping()
            logger.info("Redis connected")
        except Exception as e:
            logger.error("Redis connection failed: %s", e)
            self.redis = None
            self.pool = None
            raise

    async def disconnect(self) -> None:
        if self.redis:
            try:
                await self.redis.close()
            except Exception as e:
                logger.warning("Redis close error: %s", e)

        if self.pool:
            try:
                await self.pool.disconnect(inuse_connections=True)
            except Exception as e:
                logger.warning("Redis pool disconnect error: %s", e)

        self.redis = None
        self.pool = None
        logger.info("Redis disconnected")

    async def ping(self) -> bool:
        try:
            client = await self._get_client()
            return await client.ping() is True
        except Exception:
            return False

    async def _get_client(self) -> Redis:
        if not self.redis:
            await self.connect()

        if not self.redis:
            raise ConnectionError("Redis not available")

        try:
            await self.redis.ping()
        except Exception:
            await self.connect()

        if not self.redis:
            raise ConnectionError("Redis not available")

        return self.redis

    async def get(self, key: str, default: Any = None) -> Any:
        try:
            client = await self._get_client()
            value = await client.get(key)

            if value is None:
                return default

            return pickle.loads(value)  # noqa: S301
        except Exception as e:
            logger.error("Redis get failed: key=%s error=%s", key, type(e).__name__)
            return default

    async def set(self, key: str, value: Any, ttl: int | None = None) -> bool:
        try:
            client = await self._get_client()
            data = pickle.dumps(value)
            result = await client.set(key, data, ex=ttl)
            return result is True
        except Exception as e:
            logger.error("Redis set failed: key=%s error=%s", key, type(e).__name__)
            return False

    async def delete(self, *keys: str) -> int:
        if not keys:
            return 0

        try:
            client = await self._get_client()
            return await client.delete(*keys) or 0
        except Exception as e:
            logger.error(
                "Redis delete failed: keys=%s error=%s", keys, type(e).__name__
            )
            return 0

    async def exists(self, key: str) -> bool:
        try:
            client = await self._get_client()
            return await client.exists(key) > 0
        except Exception:
            return False

    async def incr(self, key: str, expire_if_new: int | None = None) -> int:
        try:
            client = await self._get_client()
            count: int = await client.incr(key)
            if expire_if_new is not None and count == 1:
                await client.expire(key, expire_if_new)
            return count
        except Exception as e:
            logger.error("Redis incr failed: key=%s error=%s", key, type(e).__name__)
            raise

    async def acquire_lock(self, key: str, ttl: int) -> bool:
        try:
            client = await self._get_client()
            acquired = await client.set(key, b"1", ex=ttl, nx=True)
            return acquired is True
        except Exception as e:
            logger.error(
                "Redis lock acquire failed: key=%s error=%s", key, type(e).__name__
            )
            return False

    async def release_lock(self, key: str) -> bool:
        try:
            client = await self._get_client()
            await client.delete(key)
            return True
        except Exception as e:
            logger.error(
                "Redis lock release failed: key=%s error=%s", key, type(e).__name__
            )
            return False
