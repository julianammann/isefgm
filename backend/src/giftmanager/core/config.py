from functools import lru_cache
from typing import Literal

from pydantic import PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    app_name: str = "app"
    app_env: Literal["development", "test", "production"] = "development"
    log_level: str = "INFO"
    database_url: PostgresDsn = PostgresDsn("postgresql+asyncpg://app:app@localhost:5432/app")
    cors_origins: list[str] = ["http://localhost:3000"]

    @property
    def is_dev(self) -> bool:
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    return Settings()
