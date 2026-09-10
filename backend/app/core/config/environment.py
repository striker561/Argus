from functools import lru_cache

from dotenv import load_dotenv
from pydantic_settings import BaseSettings, SettingsConfigDict

load_dotenv()


class Environment(BaseSettings):
    """Application settings with defaults for local dev; override via .env."""

    APP_NAME: str = "Argus"
    APP_CURRENT_VERSION: str = "0.1.0"
    IS_PRODUCTION: bool = False
    LOG_LEVEL: str = "INFO"

    DATABASE_URL: str = "sqlite:///./argus.db"
    DATABASE_POOL_SIZE: int = 5
    DATABASE_MAX_OVERFLOW: int = 10
    DATABASE_POOL_TIMEOUT: int = 30

    # Optional: Redis used by Argus itself for cache / pub-sub.
    REDIS_URL: str | None = None

    CORS_ORIGINS: str = "http://localhost:3000"

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
