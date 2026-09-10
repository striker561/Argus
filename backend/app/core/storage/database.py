import logging
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi.exceptions import HTTPException
from sqlalchemy.exc import SQLAlchemyError
from sqlalchemy.ext.asyncio import (
    AsyncEngine,
    AsyncSession,
    async_sessionmaker,
    create_async_engine,
)
from sqlalchemy.orm import DeclarativeBase
from sqlalchemy.pool import StaticPool

from app.core.config.environment import Environment


class Base(DeclarativeBase):
    pass


class DatabaseEngine:
    def __init__(self, database_url: str, environment: Environment) -> None:
        self.database_url = database_url
        self.environment = environment
        self.engine = self._create_engine()

    def _create_engine(self) -> AsyncEngine:
        if "postgresql" in self.database_url:
            async_url = self.database_url.replace(
                "postgresql://", "postgresql+asyncpg://", 1
            )
            return create_async_engine(
                async_url,
                pool_size=self.environment.DATABASE_POOL_SIZE,
                max_overflow=self.environment.DATABASE_MAX_OVERFLOW,
                pool_timeout=self.environment.DATABASE_POOL_TIMEOUT,
                pool_pre_ping=True,
                echo=False,
            )

        if "sqlite" in self.database_url:
            async_url = self.database_url.replace("sqlite://", "sqlite+aiosqlite://", 1)
            return create_async_engine(
                async_url,
                connect_args={"check_same_thread": False},
                poolclass=StaticPool,
                echo=False,
            )

        raise ValueError(f"Unsupported database URL: {self.database_url}")

    async def start(self, logger: logging.Logger) -> None:
        logger.info("Database started: %s", self._sanitize_url())

    async def turn_off(self, logger: logging.Logger) -> None:
        if self.engine:
            await self.engine.dispose()
            logger.info("Database shutdown complete")

    def _sanitize_url(self) -> str:
        return self.database_url.split("@")[-1]


class DBSessionManager:
    """Provides async DB sessions; commits on success, rolls back on error."""

    def __init__(self, engine: AsyncEngine, logger: logging.Logger) -> None:
        self.engine = engine
        self.logger = logger
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
        except (SQLAlchemyError, HTTPException):
            await session.rollback()
            raise
        finally:
            await session.close()
