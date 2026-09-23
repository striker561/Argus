"""Pydantic model for the argus.yaml document."""

from collections import Counter
from typing import Self

from pydantic import BaseModel, ConfigDict, Field, model_validator

from app.connectors.schema import ConnectionConfig


class ArgusConfig(BaseModel):
    """The whole argus.yaml document."""

    model_config = ConfigDict(extra="forbid")

    connections: list[ConnectionConfig] = Field(min_length=1)

    @model_validator(mode="after")
    def _reject_duplicate_names(self) -> Self:
        counts = Counter(connection.name for connection in self.connections)
        duplicates = sorted(name for name, count in counts.items() if count > 1)
        if duplicates:
            raise ValueError(f"Duplicate connection name(s): {', '.join(duplicates)}")
        return self
