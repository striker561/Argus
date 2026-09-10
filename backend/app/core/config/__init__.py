"""Configuration module - Logger and environment settings."""

import logging

from app.core.config.environment import Environment, get_environment
from app.core.config.logger import get_logger

# Core configuration exports
logger: logging.Logger = get_logger()
environment: Environment = get_environment()

__all__ = ["environment", "get_environment", "get_logger", "logger"]
