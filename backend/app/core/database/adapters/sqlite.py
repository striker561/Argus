from sqlalchemy.ext.asyncio import AsyncEngine, create_async_engine
from sqlalchemy.pool import StaticPool

from .base import DatabaseAdapter


class SQLiteAdapter(DatabaseAdapter):
    def create_engine(self, database_url: str) -> AsyncEngine:
        return create_async_engine(
            database_url,
            connect_args={"check_same_thread": False},
            poolclass=StaticPool,
            echo=False,
        )
