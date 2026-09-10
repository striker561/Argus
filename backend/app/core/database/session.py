"""Handles the session creation and basically how sessions are managed"""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from sqlalchemy.ext.asyncio import AsyncEngine, AsyncSession, async_sessionmaker


class DatabaseSession:
    """Provides async DB sessions; commits on success, rolls back on error."""

    def __init__(self, engine: AsyncEngine) -> None:
        self.engine = engine
        self.async_session_factory = async_sessionmaker(
            engine,
            expire_on_commit=False,
            autoflush=True,
            class_=AsyncSession,
        )

    @asynccontextmanager
    async def session(
        self, *, no_commit: bool = False
    ) -> AsyncGenerator[AsyncSession, None]:
        session = self.async_session_factory()
        try:
            yield session
            if not no_commit:
                await session.commit()
        except Exception:
            await session.rollback()
            raise
        finally:
            await session.close()
