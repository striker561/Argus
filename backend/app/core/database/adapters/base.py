"""Base database adapter that all adapters uses"""

from abc import ABC, abstractmethod

from sqlalchemy.ext.asyncio import AsyncEngine


class DatabaseAdapter(ABC):
    @abstractmethod
    def create_engine(self, database_url: str) -> AsyncEngine: ...
