"""Application settings from environment variables and `.env`."""

from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime configuration.

    Read from the process environment, `.env` in the working directory or `../.env`
    (repo root). The field descriptions are rendered into docs/generated/konfiguration.md.
    """

    model_config = SettingsConfigDict(
        env_file=(".env", "../.env"),
        env_file_encoding="utf-8",
        extra="ignore",
    )

    # `description` is user-facing: export_docs.py renders it into the operations
    # manual (docs/generated/configuration.md).
    app_name: str = Field(
        default="Geschenke-Manager API",
        description="Title in OpenAPI and in the Swagger UI.",
    )
    app_env: Literal["development", "test", "production"] = Field(
        default="production",
        description="`development` enables `/docs`, `/openapi.json` and console logs and sends "
        "the session cookie as `session` without `Secure`; `production` and `test` write JSON "
        "logs and send it as `__Host-session` with `Secure`. "
        "Unset means `production`; `mise run dev` and `compose.override.yaml` set `development`.",
    )
    log_level: Literal["DEBUG", "INFO", "WARNING", "ERROR"] = Field(
        default="INFO", description="Log threshold for the app, Uvicorn, SQLAlchemy and Alembic."
    )
    database_url: PostgresDsn = Field(
        default=PostgresDsn("postgresql+asyncpg://app:app@localhost:5432/app"),
        description="PostgreSQL connection. The `asyncpg` driver is required.",
    )
    default_timezone: str = Field(
        default="Europe/Berlin",
        description="Time zone in which the scheduler evaluates calendar dates (birthdays, "
        "occasions). Storage is in UTC (Q-08).",
    )
    uploads_dir: Path = Field(
        default=Path("data/uploads"),
        description="Storage for image uploads; a volume in production. "
        "The database only holds metadata.",
    )
    session_ttl_days: int = Field(
        default=14,
        description="Session lifetime in days; extended on every use, "
        "up to `SESSION_MAX_LIFETIME_DAYS`.",
    )
    session_max_lifetime_days: int = Field(
        default=30,
        description="Hard upper bound on a session's age in days, counted from login, "
        "however often the session is used. After that the user must log in again.",
    )

    @property
    def session_ttl(self) -> timedelta:
        """Session lifetime as a `timedelta`."""
        return timedelta(days=self.session_ttl_days)

    @property
    def session_max_lifetime(self) -> timedelta:
        """Absolute session lifetime as a `timedelta`."""
        return timedelta(days=self.session_max_lifetime_days)

    @property
    def is_dev(self) -> bool:
        """True in development: `/docs`, `/openapi.json`, console logs, non-`Secure` cookies."""
        return self.app_env == "development"


@lru_cache
def get_settings() -> Settings:
    """Return the process-wide settings, read once and cached."""
    return Settings()
