"""Base queue adapter that all stack adapters implement."""

from abc import ABC, abstractmethod

from redis.asyncio import Redis

from app.connectors.adapters.exceptions import ConnectorConnectionError
from app.connectors.adapters.schema import JobDetail, JobSummary, QueueSummary
from app.connectors.schema import ConnectionConfig
from app.core.redis.client import RedisClient


class QueueAdapter(ABC):
    """Inspects one monitored Redis instance for a single stack.

    Subclasses map that stack's storage layout onto the shared schemas.
    """

    def __init__(self, connection: ConnectionConfig) -> None:
        self.connection = connection
        self._client = RedisClient(connection.redis_url)

    @property
    def name(self) -> str:
        """Name of the connection in ``argus.yaml``."""
        return self.connection.name

    @property
    def stack(self) -> str:
        """Stack of the connection in ``argus.yaml``."""
        return self.connection.stack.value

    @property
    def prefix(self) -> str:
        """Key prefix the stack prepends, or an empty string."""
        return self.connection.prefix

    async def connect(self) -> RedisClient:
        """Connect the Redis client for this connection, or reuse it."""
        try:
            await self._client.connect()
        except Exception as e:
            raise ConnectorConnectionError(
                f"Could not connect to '{self.connection.name}' "
                f"({self.connection.redis_url}): {e}"
            ) from e

        return self._client

    async def close(self) -> None:
        """Release the Redis client."""
        await self._client.disconnect()

    async def redis(self) -> Redis:
        """Return the raw client, connecting first if needed.
        For raw granular commands that the redis cli offer directly
        """
        client = await self.connect()
        raw = client.redis
        if raw is None:
            raise ConnectorConnectionError(f"'{self.name}' is not connected")

        return raw

    @abstractmethod
    async def list_queues(self) -> list[QueueSummary]:
        """Return queue names + counts only. No payloads, no job IDs."""

    @abstractmethod
    async def list_jobs(
        self, queue: str, offset: int = 0, limit: int = 50
    ) -> list[JobSummary]:
        """Return a page of job IDs + minimal metadata. No full payloads."""

    @abstractmethod
    async def get_job(self, job_id: str) -> JobDetail:
        """Return the full payload for one job, for the inspect view."""

    @abstractmethod
    async def list_failed_jobs(
        self, queue: str | None = None, offset: int = 0, limit: int = 50
    ) -> list[JobSummary]:
        """Return failed jobs, optionally scoped to a single queue."""

    @abstractmethod
    async def replay_job(self, job_id: str) -> None:
        """Requeue a failed job.

        Raises ``JobNotFoundError`` or ``ReplayFailedError`` rather than
        returning a falsy value.
        """
