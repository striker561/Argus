"""Dependencies and lifecycle helpers for the database."""

from collections.abc import AsyncGenerator
from typing import Annotated

from fastapi import Depends
from sqlalchemy.ext.asyncio import AsyncSession

from app.core.config import environment, logger
from app.core.database.engine import DatabaseEngine
from app.core.database.factory import DatabaseAdapterFactory
from app.core.database.session import DatabaseSession

_engine: DatabaseEngine | None = None
_session_manager: DatabaseSession | None = None


def get_database_engine() -> DatabaseEngine:
    """Build the engine once (fails fast if the driver is unsupported)."""
    global _engine
    if _engine is None:
        adapter = DatabaseAdapterFactory.create()
        _engine = DatabaseEngine(adapter, environment.DATABASE_URL)
        logger.info("Database engine ready: %s", type(adapter).__name__)
    return _engine


def get_session_manager() -> DatabaseSession:
    """Session manager bound to the singleton engine."""
    global _session_manager
    if _session_manager is None:
        _session_manager = DatabaseSession(get_database_engine().engine)
    return _session_manager


async def get_db() -> AsyncGenerator[AsyncSession, None]:
    """Yield a request-scoped session (commits on success, rolls back on error)."""
    async with get_session_manager().session() as session:
        yield session


DBSessionDep = Annotated[AsyncSession, Depends(get_db)]


async def init_database() -> None:
    """Eagerly build the engine so a bad driver fails at startup."""
    get_database_engine()


async def shutdown_database() -> None:
    """Dispose the engine and clear the singletons."""
    global _engine, _session_manager
    if _engine is not None:
        await _engine.turn_off()
    _engine = None
    _session_manager = None
