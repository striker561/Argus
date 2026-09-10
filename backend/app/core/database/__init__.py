"""Database package: declarative base, sessions, and dependency wiring."""

from app.core.database.base import Base as Base
from app.core.database.dependencies import (
    DBSessionDep as DBSessionDep,
    get_db as get_db,
    init_database as init_database,
    shutdown_database as shutdown_database,
)
from app.core.database.session import DatabaseSession as DatabaseSession

__all__ = [
    "Base",
    "DBSessionDep",
    "DatabaseSession",
    "get_db",
    "init_database",
    "shutdown_database",
]
