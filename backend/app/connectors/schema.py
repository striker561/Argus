from pydantic import BaseModel, ConfigDict, Field

from app.connectors.enums import Stack


class ConnectionConfig(BaseModel):
    """A single Redis instance Argus should monitor."""

    model_config = ConfigDict(extra="forbid")

    name: str = Field(min_length=1)
    redis_url: str = Field(min_length=1)
    stack: Stack
