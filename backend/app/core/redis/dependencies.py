"""FastAPI dependencies for Redis access."""

from typing import Annotated

from fastapi import Depends

from app.core.config import environment
from app.core.redis.client import RedisClient

_redis: RedisClient | None = None


def get_redis() -> RedisClient:
    """Redis client built once from the configured URL."""
    global _redis
    if _redis is None:
        _redis = RedisClient(environment.REDIS_URL)
    return _redis


RedisDep = Annotated[RedisClient, Depends(get_redis)]
