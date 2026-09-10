"""Core exports — configuration, logging, and storage dependencies."""

from app.core.app import app as app
from app.core.config import environment as environment
from app.core.config import logger as logger
from app.core.storage import (
    Base as Base,
    DBSessionManager as DBSessionManager,
    DatabaseEngine as DatabaseEngine,
    RedisCache as RedisCache,
    get_database_engine as get_database_engine,
    get_db as get_db,
    get_redis_cache as get_redis_cache,
    get_session_manager as get_session_manager,
)

__all__ = [
    "app",
    "Base",
    "DBSessionManager",
    "DatabaseEngine",
    "RedisCache",
    "environment",
    "get_database_engine",
    "get_db",
    "get_redis_cache",
    "get_session_manager",
    "logger",
]
