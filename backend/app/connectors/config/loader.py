"""Locate, read, interpolate and validate argus.yaml."""

import os
import re
from pathlib import Path
from typing import Any

import yaml
from pydantic import ValidationError

from app.connectors.config.exceptions import (
    ConfigError,
    ConfigFileNotFoundError,
    MissingEnvVarError,
)
from app.connectors.config.schema import ArgusConfig
from app.core.config import environment
from app.core.config.environment import Environment

_ENV_REFERENCE = re.compile(r"\$\{([A-Za-z_][A-Za-z0-9_]*)\}")


class ArgusConfigLoader:
    """Loads an argus.yaml file into a validated :class:`ArgusConfig`."""

    def __init__(
        self,
        path: Path | str | None = None,
        settings: Environment | None = None,
    ) -> None:
        self._path = path
        self._settings = settings if settings is not None else environment

    def resolve_path(self) -> Path:
        """Resolve the path: explicit arg, else the ARGUS_CONFIG_PATH setting."""
        if self._path is not None:
            return Path(self._path)
        return Path(self._settings.ARGUS_CONFIG_PATH)

    def load(self) -> ArgusConfig:
        """Read and validate the config, raising ConfigError on any problem."""
        config_path = self.resolve_path()
        data = self._parse(self._read(config_path), config_path)
        try:
            return ArgusConfig.model_validate(self._interpolate(data))
        except ValidationError as exc:
            raise ConfigError(
                f"Invalid configuration in {config_path}:\n{exc}"
            ) from exc

    @staticmethod
    def _read(config_path: Path) -> str:
        try:
            return config_path.read_text(encoding="utf-8")
        except FileNotFoundError as exc:
            raise ConfigFileNotFoundError(
                f"Config file not found: {config_path} "
                "(copy argus.example.yaml or set ARGUS_CONFIG_PATH)"
            ) from exc
        except OSError as exc:
            raise ConfigError(
                f"Could not read config file {config_path}: {exc}"
            ) from exc

    @staticmethod
    def _parse(raw: str, config_path: Path) -> dict[str, Any]:
        try:
            data = yaml.safe_load(raw)
        except yaml.YAMLError as exc:
            raise ConfigError(f"Invalid YAML in {config_path}: {exc}") from exc
        if not isinstance(data, dict):
            raise ConfigError(f"Config file {config_path} must contain a YAML mapping")
        return data

    @classmethod
    def _interpolate(cls, value: Any) -> Any:
        """Replace every ${VAR} in string values with its environment value."""
        if isinstance(value, str):
            return _ENV_REFERENCE.sub(cls._replace_env_reference, value)
        if isinstance(value, dict):
            return {key: cls._interpolate(item) for key, item in value.items()}
        if isinstance(value, list):
            return [cls._interpolate(item) for item in value]
        return value

    @staticmethod
    def _replace_env_reference(match: re.Match[str]) -> str:
        name = match.group(1)
        if name not in os.environ:
            raise MissingEnvVarError(f"Environment variable '{name}' is not set")
        return os.environ[name]
