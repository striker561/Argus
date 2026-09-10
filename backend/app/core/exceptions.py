"""Exception handling helpers."""

from collections.abc import Sequence
from typing import Any


def format_validation_errors(errors: Sequence[Any]) -> dict[str, list[str]]:
    formatted: dict[str, list[str]] = {}
    for error in errors:
        loc = ".".join(str(part) for part in error.get("loc", [])) or "_"
        formatted.setdefault(loc, []).append(str(error.get("msg", "Invalid value")))
    return formatted
