"""Logging via the standard library, written to stdout only."""

import logging
import sys
from functools import lru_cache

from app.core.config.environment import get_environment

_FORMAT = "%(asctime)s | %(levelname)-8s | %(message)s"


@lru_cache(maxsize=1)
def get_logger() -> logging.Logger:
    settings = get_environment()
    name = settings.APP_NAME or "argus"
    level = getattr(logging, settings.LOG_LEVEL.upper(), logging.INFO)

    logger = logging.getLogger(name)
    logger.setLevel(level)

    if not logger.handlers:
        handler = logging.StreamHandler(sys.stdout)
        handler.setFormatter(logging.Formatter(_FORMAT))
        logger.addHandler(handler)

    # Don't duplicate output into any root handler.
    logger.propagate = False
    return logger
