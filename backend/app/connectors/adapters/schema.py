"""Stack-neutral shapes returned by every queue adapter."""

from datetime import datetime
from typing import Any

from pydantic import BaseModel, Field


class QueueSummary(BaseModel):
    """Per-queue job counts."""

    name: str
    pending: int = 0
    reserved: int = 0
    delayed: int = 0
    failed: int = 0


class JobSummary(BaseModel):
    """Minimal metadata for one job, as shown in a list view."""

    job_id: str
    queue: str
    attempts: int = 0
    pushed_at: datetime | None = None


class JobDetail(JobSummary):
    """A single job including its full payload, for the inspect view."""

    payload: dict[str, Any] = Field(default_factory=dict)
    payload_size_bytes: int = 0
    complexity_score: int = 0
