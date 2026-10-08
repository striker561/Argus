"""Laravel Redis queue adapter."""

import json
from datetime import UTC, datetime
from typing import Any

from app.connectors.adapters.base import QueueAdapter
from app.connectors.adapters.exceptions import JobNotFoundError, ReplayFailedError
from app.connectors.adapters.schema import JobDetail, JobSummary, QueueSummary

QUEUES = "queues:"
ROLES = ((":reserved", "reserved"), (":delayed", "delayed"), (":notify", "notify"))
SCAN_COUNT = 500


class LaravelQueueAdapter(QueueAdapter):
    """Adapter for Laravel's Redis queue driver (``RedisQueue``)."""

    async def list_queues(self) -> list[QueueSummary]:
        """Return every queue found under ``{prefix}queues:*``."""
        redis = await self.redis()
        found: dict[str, QueueSummary] = {}

        async for raw_key in redis.scan_iter(
            match=f"{self.prefix}{QUEUES}*", count=SCAN_COUNT
        ):
            name, role = self._split(raw_key.decode())
            if role == "notify":
                continue

            summary = found.setdefault(name, QueueSummary(name=name))
            if role == "pending":
                summary.pending = await redis.llen(raw_key)
            elif role == "reserved":
                summary.reserved = await redis.zcard(raw_key)
            else:
                summary.delayed = await redis.zcard(raw_key)

        return [found[name] for name in sorted(found)]

    async def list_jobs(
        self, queue: str, offset: int = 0, limit: int = 50
    ) -> list[JobSummary]:
        """Return a page of the pending jobs of ``queue``."""
        redis = await self.redis()
        members = await redis.lrange(
            self._pending_key(queue), offset, offset + limit - 1
        )

        summaries: list[JobSummary] = []
        for member in members:
            payload = self._parse(member)
            if payload is not None:
                summaries.append(self._to_summary(payload, queue))

        return summaries

    # At scale this will bite especially the members the lrange and zrange
    # that list all till the end It will be further optimized, would revert
    # to this Later, reading a 500kJobs would be a problem
    async def get_job(self, job_id: str, queue: str) -> JobDetail:
        """Return one job from the pending, reserved or delayed keys."""
        redis = await self.redis()

        async for raw_key in redis.scan_iter(
            match=f"{self.prefix}{QUEUES}{queue}*", count=SCAN_COUNT
        ):
            name, role = self._split(raw_key.decode())
            if role == "notify":
                continue

            members = (
                await redis.lrange(raw_key, 0, -1)
                if role == "pending"
                else await redis.zrange(raw_key, 0, -1)
            )
            for member in members:
                payload = self._parse(member)
                if payload is not None and self._job_id(payload) == job_id:
                    return self._to_detail(payload, name, member)

        raise JobNotFoundError(f"No job '{job_id}' in connection '{self.name}'")

    async def list_failed_jobs(
        self, queue: str | None = None, offset: int = 0, limit: int = 50
    ) -> list[JobSummary]:
        """Return nothing: Laravel keeps failed jobs in its SQL table."""
        return []

    async def replay_job(self, job_id: str) -> None:
        """Raise: replaying a Laravel job needs its SQL table."""
        raise ReplayFailedError(
            f"Connection '{self.name}' only has Redis; Laravel replays failed "
            "jobs from its 'failed_jobs' table"
        )

    def _pending_key(self, name: str) -> str:
        """Return the key holding the pending payloads of ``name``."""
        return f"{self.prefix}{QUEUES}{name}"

    def _split(self, key: str) -> tuple[str, str]:
        """Return the queue name and role encoded in ``key``."""
        rest = key[len(self.prefix) + len(QUEUES) :]
        for suffix, role in ROLES:
            if rest.endswith(suffix):
                return rest[: -len(suffix)], role

        return rest, "pending"

    @staticmethod
    def _parse(member: bytes) -> dict[str, Any] | None:
        """Decode a queue member as a JSON object, or return ``None``."""
        try:
            payload = json.loads(member)
        except (json.JSONDecodeError, UnicodeDecodeError):
            return None

        return payload if isinstance(payload, dict) else None

    @staticmethod
    def _job_id(payload: dict[str, Any]) -> str:
        """Return the job id from ``payload``, falling back to its uuid."""
        return str(payload.get("id") or payload.get("uuid") or "")

    def _to_summary(self, payload: dict[str, Any], queue: str) -> JobSummary:
        """Map a payload onto :class:`JobSummary`."""
        created = payload.get("createdAt")
        return JobSummary(
            job_id=self._job_id(payload),
            queue=queue,
            attempts=int(payload.get("attempts") or 0),
            pushed_at=(
                datetime.fromtimestamp(int(created), tz=UTC)
                if isinstance(created, int | float)
                else None
            ),
        )

    def _to_detail(
        self, payload: dict[str, Any], queue: str, member: bytes
    ) -> JobDetail:
        """Map a payload onto :class:`JobDetail`."""
        return JobDetail(
            **self._to_summary(payload, queue).model_dump(),
            payload=payload,
            payload_size_bytes=len(member),
        )
