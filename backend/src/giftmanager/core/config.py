"""Application settings from environment variables and `.env`."""

from datetime import timedelta
from functools import lru_cache
from pathlib import Path
from typing import Literal

from pydantic import Field, PostgresDsn, SecretStr, field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict


class Settings(BaseSettings):
    """Typed runtime configuration.

    Read from the process environment, `.env` in the working directory or `../.env`
    (repo root). The field descriptions are rendered into docs/generated/configuration.md.
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
    smtp_host: str = Field(
        default="localhost",
        description="SMTP server host for outgoing mail. The default points at a local Mailpit.",
    )
    smtp_port: int = Field(
        default=1025,
        description="SMTP server port. Typical values: 1025 for Mailpit, 587 for STARTTLS, "
        "465 for implicit TLS.",
    )
    smtp_security: Literal["none", "starttls", "tls"] = Field(
        default="none",
        description="Transport security for SMTP. `none` for Mailpit, `starttls` for port 587, "
        "`tls` for port 465 (implicit TLS, e.g. Resend).",
    )
    smtp_username: str | None = Field(
        default=None,
        description="SMTP login name. Leave unset when the server needs no authentication.",
    )
    smtp_password: SecretStr | None = Field(
        default=None,
        description="SMTP login password. Never shown in `repr()`; log tracebacks omit local variables.",
    )
    smtp_from: str = Field(
        default="Geschenke-Manager <noreply@isefgm.localhost>",
        description="Sender address on outgoing mail, in `Name <address>` form. "
        "Production sets it via the deployment (SMTP_FROM).",
    )
    smtp_timeout_seconds: int = Field(
        default=30,
        description="Timeout in seconds for connecting to and talking to the SMTP server.",
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
    registration_enabled: bool = Field(
        default=False,
        description="`true` opens `POST /api/v1/auth/register` and the sign-up page; "
        "otherwise the endpoint returns 403 and the frontend hides the link (it reads the "
        "same variable). Accounts can always be created with `mise run create-user`.",
    )

    origin: str = Field(
        default="http://localhost:3000",
        description="Public address of the app, used for links in mails. "
        "Same value as the frontend's `ORIGIN`.",
    )

    @field_validator("origin")
    @classmethod
    def _strip_trailing_slash(cls, value: str) -> str:
        return value.rstrip("/")

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
