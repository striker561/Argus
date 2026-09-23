"""Tests for locating, reading and validating argus.yaml."""

from pathlib import Path

import pytest

from app.connectors.config import ArgusConfigLoader
from app.connectors.config.exceptions import (
    ConfigError,
    ConfigFileNotFoundError,
    MissingEnvVarError,
)
from app.core.config.environment import Environment

MINIMAL = """
connections:
  - name: my-app
    redis_url: redis://localhost:6379
    stack: laravel
"""


def _write(path: Path, text: str) -> Path:
    path.write_text(text, encoding="utf-8")
    return path


def test_minimal_config_is_loaded(tmp_path: Path) -> None:
    config = ArgusConfigLoader(_write(tmp_path / "argus.yaml", MINIMAL)).load()
    assert [c.name for c in config.connections] == ["my-app"]
    assert config.connections[0].stack == "laravel"


def test_env_reference_is_interpolated(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setenv("ARGUS_TEST_REDIS_URL", "redis://:secret@host:6379")
    path = _write(
        tmp_path / "argus.yaml",
        "connections:\n"
        "  - name: prod\n"
        "    redis_url: ${ARGUS_TEST_REDIS_URL}\n"
        "    stack: arq\n",
    )
    config = ArgusConfigLoader(path).load()
    assert config.connections[0].redis_url == "redis://:secret@host:6379"


def test_missing_env_reference_fails(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ARGUS_TEST_MISSING", raising=False)
    path = _write(
        tmp_path / "argus.yaml",
        "connections:\n"
        "  - name: prod\n"
        "    redis_url: ${ARGUS_TEST_MISSING}\n"
        "    stack: laravel\n",
    )
    with pytest.raises(MissingEnvVarError):
        ArgusConfigLoader(path).load()


def test_duplicate_names_fail(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "argus.yaml",
        "connections:\n"
        "  - name: dup\n"
        "    redis_url: redis://localhost:6379\n"
        "    stack: laravel\n"
        "  - name: dup\n"
        "    redis_url: redis://localhost:6380\n"
        "    stack: arq\n",
    )
    with pytest.raises(ConfigError, match="Duplicate"):
        ArgusConfigLoader(path).load()


def test_unknown_stack_fails(tmp_path: Path) -> None:
    path = _write(
        tmp_path / "argus.yaml",
        "connections:\n"
        "  - name: x\n"
        "    redis_url: redis://localhost:6379\n"
        "    stack: celery\n",
    )
    with pytest.raises(ConfigError):
        ArgusConfigLoader(path).load()


def test_unknown_top_level_key_fails(tmp_path: Path) -> None:
    path = _write(tmp_path / "argus.yaml", MINIMAL + "extra: 1\n")
    with pytest.raises(ConfigError):
        ArgusConfigLoader(path).load()


def test_empty_connections_fail(tmp_path: Path) -> None:
    path = _write(tmp_path / "argus.yaml", "connections: []\n")
    with pytest.raises(ConfigError):
        ArgusConfigLoader(path).load()


def test_malformed_yaml_fails(tmp_path: Path) -> None:
    path = _write(tmp_path / "argus.yaml", "connections: [unclosed\n")
    with pytest.raises(ConfigError):
        ArgusConfigLoader(path).load()


def test_missing_file_fails(tmp_path: Path) -> None:
    with pytest.raises(ConfigFileNotFoundError):
        ArgusConfigLoader(tmp_path / "nope.yaml").load()


def test_path_from_settings(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> None:
    target = _write(tmp_path / "from_settings.yaml", MINIMAL)
    monkeypatch.setenv("ARGUS_CONFIG_PATH", str(target))
    config = ArgusConfigLoader(settings=Environment()).load()
    assert config.connections[0].name == "my-app"


def test_explicit_path_beats_settings(tmp_path: Path) -> None:
    _write(tmp_path / "other.yaml", MINIMAL)
    explicit = _write(
        tmp_path / "explicit.yaml",
        "connections:\n"
        "  - name: explicit\n"
        "    redis_url: redis://localhost:6379\n"
        "    stack: arq\n",
    )
    settings = Environment(ARGUS_CONFIG_PATH=tmp_path / "other.yaml")
    config = ArgusConfigLoader(explicit, settings=settings).load()
    assert config.connections[0].name == "explicit"


def test_default_path_is_cwd_argus_yaml(
    tmp_path: Path, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.delenv("ARGUS_CONFIG_PATH", raising=False)
    monkeypatch.chdir(tmp_path)
    _write(tmp_path / "argus.yaml", MINIMAL)
    loader = ArgusConfigLoader(settings=Environment())
    assert loader.resolve_path() == Path("argus.yaml")
    assert loader.load().connections[0].name == "my-app"
