from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine

from app.core.config.environment import Environment

from .base import DatabaseAdapter


class PostgreSQLAdapter(DatabaseAdapter):
    def __init__(self, environment: Environment) -> None:
        self.environment = environment

    def create_engine(self, database_url: str) -> AsyncEngine:
        return create_async_engine(
            database_url,
            pool_size=self.environment.DATABASE_POOL_SIZE,
            max_overflow=self.environment.DATABASE_MAX_OVERFLOW,
            pool_timeout=self.environment.DATABASE_POOL_TIMEOUT,
            pool_pre_ping=True,
            echo=False,
        )
