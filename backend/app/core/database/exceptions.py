"""Database exceptions."""


class UnsupportedDatabaseError(ValueError):
    """Raised at startup when no adapter matches the database URL."""

    def __init__(self, database_url: str) -> None:
        super().__init__(f"Unsupported database URL: {database_url}")
        self.database_url = database_url
