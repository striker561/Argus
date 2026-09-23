"""Dependencies for the argus.yaml configuration."""

from pathlib import Path
from typing import Annotated

from fastapi import Depends

from app.connectors.config.loader import ArgusConfigLoader
from app.connectors.config.schema import ArgusConfig
from app.core.config import logger

_config: ArgusConfig | None = None


def _load(path: Path | str | None = None) -> ArgusConfig:
    """Load argus.yaml; an explicit path overrides the ARGUS_CONFIG_PATH setting."""
    loader = ArgusConfigLoader(path)
    config = loader.load()
    logger.info(
        "Loaded %d connection(s) from %s",
        len(config.connections),
        loader.resolve_path(),
    )
    return config


def get_argus_config() -> ArgusConfig:
    """Return the parsed argus.yaml, loading it on first use."""
    global _config
    if _config is None:
        _config = _load()
    return _config


ArgusConfigDep = Annotated[ArgusConfig, Depends(get_argus_config)]


def init_argus_config(path: Path | str | None = None) -> None:
    """Load argus.yaml at startup so config errors fail fast.

    Pass ``path`` to override the ``ARGUS_CONFIG_PATH`` setting.
    """
    global _config
    if _config is None:
        _config = _load(path)
