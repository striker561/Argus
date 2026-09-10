"""Database Engine that starts the database"""

from app.core.database.adapters.base import DatabaseAdapter


class DatabaseEngine:
    def __init__(
        self,
        adapter: DatabaseAdapter,
        database_url: str,
    ) -> None:
        self.adapter = adapter
        self.database_url = database_url

        self.engine = self.adapter.create_engine(self.database_url)

    async def turn_off(self) -> None:
        await self.engine.dispose()
