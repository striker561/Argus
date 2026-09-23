from functools import lru_cache
from pathlib import Path

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Environment(BaseSettings):
    """Application settings with defaults for local dev; override via .env."""

    APP_NAME: str = "Argus"
    APP_CURRENT_VERSION: str = "0.1.0"
    IS_PRODUCTION: bool = False
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "sqlite+aiosqlite:///./argus.db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

    # Redis to monitor — required: Argus reads the job queues from here.
    REDIS_URL: str = "redis://localhost:6379/0"

    CORS_ORIGINS: str = "http://localhost:3000"

    # Path to argus.yaml (relative paths resolve against the cwd).
    ARGUS_CONFIG_PATH: Path = Path("argus.yaml")

    model_config = SettingsConfigDict(
        case_sensitive=True,
        env_file=".env",
        env_file_encoding="utf-8",
        extra="ignore",
    )

    @property
    def cors_origins_list(self) -> list[str]:
        return [
            origin.strip() for origin in self.CORS_ORIGINS.split(",") if origin.strip()
        ]


@lru_cache
def get_environment() -> Environment:
    return Environment()
