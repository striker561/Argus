"""Errors raised while loading the Argus configuration file."""


class ConfigError(Exception):
    """Raised when the config file cannot be read or is invalid."""


class ConfigFileNotFoundError(ConfigError):
    """Raised when the config file does not exist."""


class MissingEnvVarError(ConfigError):
    """Raised when a ${VAR} reference cannot be resolved from the environment."""
