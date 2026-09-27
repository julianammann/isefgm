"""Accounts and server-side sessions."""

import enum
import uuid
from datetime import datetime

from sqlalchemy import DateTime, Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column, relationship

from giftmanager.models.base import Base, TimestampMixin

# `comment=` on tables and columns is documentation, not code: Alembic writes it
# into PostgreSQL and export_docs.py renders it into docs/generated/database.md
# for MS 4.


class UserStatus(enum.StrEnum):
    """Lifecycle state of an account."""

    ACTIVE = "active"
    # Kept as a tombstone only while the account deletion (F-17) runs; the row
    # and every owned row disappear with the final DELETE.
    DELETED = "deleted"


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persist enum VALUES ("active"), not member names ("ACTIVE")."""
    return [str(member.value) for member in enum_cls]


class User(TimestampMixin, Base):
    """Account (F-01). Every domain table hangs off `owner_id -> user_account.id`.

    Named user_account, not user: `user` is reserved in PostgreSQL and would need
    quoting in every hand-written query and runbook.
    """

    __tablename__ = "user_account"
    __table_args__ = {  # noqa: RUF012 - declarative config, not state
        "comment": "User account (F-01). Every domain table belongs to exactly one account via "
        "owner_id; deleting the account deletes all of its data (F-17)."
    }

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid7, comment="Primary key, UUIDv7."
    )
    # Stored lowercased by the service; the unique constraint then covers case variants.
    email: Mapped[str] = mapped_column(
        String(320),
        unique=True,
        comment="Login name. Stored lowercased and unique.",
    )
    password_hash: Mapped[str] = mapped_column(
        String(255),
        comment="Argon2id hash of the password (Q-03). The password itself is never stored.",
    )
    display_name: Mapped[str] = mapped_column(
        String(100), comment="Display name in the UI and in notifications."
    )
    # Values in the CHECK constraint match docs/datenmodell.md, the
    # server_default and any hand-written SQL.
    status: Mapped[UserStatus] = mapped_column(
        Enum(
            UserStatus,
            name="user_status",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=_enum_values,
        ),
        default=UserStatus.ACTIVE,
        server_default=UserStatus.ACTIVE.value,
        comment="`active` or `deleted`. `deleted` only marks an account while it is being deleted.",
    )

    sessions: Mapped[list[UserSession]] = relationship(
        back_populates="user", cascade="all, delete-orphan", passive_deletes=True
    )


class UserSession(TimestampMixin, Base):
    """Server-side session. Only the SHA-256 of the cookie token is stored."""

    __tablename__ = "user_session"
    __table_args__ = {  # noqa: RUF012 - declarative config, not state
        "comment": "Server-side session. One cookie token maps to exactly "
        "one row; logging out deletes the row."
    }

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid7, comment="Primary key, UUIDv7."
    )
    user_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        index=True,
        comment="Account the session belongs to. Deleted together with the account.",
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        comment="SHA-256 of the cookie token. Only the browser knows the token itself.",
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        comment="Expiry time (UTC). The session is rejected afterwards.",
    )
    last_seen_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        comment="Last use (UTC), updated at most every five minutes.",
    )

    user: Mapped[User] = relationship(back_populates="sessions")
