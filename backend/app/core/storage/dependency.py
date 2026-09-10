"""Database and cache dependencies for the application."""

from collections.abc import AsyncGenerator

from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import environment, logger
from app.core.storage.database import DatabaseEngine, DBSessionManager
from app.core.storage.redis import RedisCache

_database_engine: DatabaseEngine | None = None
_session_manager: DBSessionManager | None = None
_redis_cache: RedisCache | None = None


def get_database_engine() -> DatabaseEngine:
    global _database_engine
    if _database_engine is None:
        _database_engine = DatabaseEngine(environment.DATABASE_URL, environment)
    return _database_engine


def get_session_manager() -> DBSessionManager:
    global _session_manager
    if _session_manager is None:
        from app.core.storage.database import DBSessionManager

        engine = get_database_engine()
        _session_manager = DBSessionManager(engine.engine, logger)
    return _session_manager


def get_redis_cache() -> RedisCache:
    global _redis_cache
    if _redis_cache is None:
        from app.core.storage.redis import RedisCache

        _redis_cache = RedisCache(environment.REDIS_URL)
    return _redis_cache


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    session_manager = get_session_manager()
    async with session_manager.session() as session:
        yield session


def get_redis() -> RedisCache:
    return get_redis_cache()
