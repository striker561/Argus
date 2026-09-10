"""Database adapter factory: picks an adapter from the configured database URL."""

from collections.abc import Callable
from typing import ClassVar

from app.core.config.environment import Environment, get_environment
from app.core.database.adapters.base import DatabaseAdapter
from app.core.database.adapters.postgresql import PostgreSQLAdapter
from app.core.database.adapters.sqlite import SQLiteAdapter
from app.core.database.exceptions import UnsupportedDatabaseError

AdapterBuilder = Callable[[Environment], DatabaseAdapter]


class DatabaseAdapterFactory:
    """Resolves a database URL to the adapter that can build its engine."""

    _builders: ClassVar[dict[str, AdapterBuilder]] = {
        "sqlite": lambda _environment: SQLiteAdapter(),
        "postgresql": lambda environment: PostgreSQLAdapter(environment),
    }

    _ALIASES: ClassVar[dict[str, str]] = {"postgres": "postgresql"}

    @classmethod
    def create(
        cls,
        database_url: str | None = None,
        *,
        environment: Environment | None = None,
    ) -> DatabaseAdapter:
        """Return the adapter for ``database_url`` (defaults to settings)."""
        settings = environment or get_environment()
        url = database_url or settings.DATABASE_URL
        builder = cls._builders.get(cls.detect_driver(url))
        if builder is None:
            raise UnsupportedDatabaseError(url)
        return builder(settings)

    @classmethod
    def detect_driver(cls, database_url: str) -> str:
        """Return the base driver name, ignoring any async-driver suffix."""
        scheme = database_url.split("://", 1)[0].lower()
        base = scheme.split("+", 1)[0]
        return cls._ALIASES.get(base, base)
