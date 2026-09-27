"""Declarative base with a constraint naming convention, and shared mixins."""

from datetime import datetime

from sqlalchemy import DateTime, MetaData, func
from sqlalchemy.orm import DeclarativeBase, Mapped, mapped_column

NAMING_CONVENTION = {
    "ix": "ix_%(column_0_label)s",
    "uq": "uq_%(table_name)s_%(column_0_name)s",
    "ck": "ck_%(table_name)s_%(constraint_name)s",
    "fk": "fk_%(table_name)s_%(column_0_name)s_%(referred_table_name)s",
    "pk": "pk_%(table_name)s",
}


class Base(DeclarativeBase):
    """Declarative base for all models; constraint names follow `NAMING_CONVENTION`.

    Fixed names keep Alembic migrations deterministic across machines.
    """

    metadata = MetaData(naming_convention=NAMING_CONVENTION)


class TimestampMixin:
    """Technical timestamps are UTC-aware (Q-08); the database sets them on insert.

    eager_defaults fetches server-generated values with the INSERT (RETURNING), so
    reading `created_at` after `flush()` never triggers implicit IO in async code.
    """

    __mapper_args__ = {"eager_defaults": True}  # noqa: RUF012 - declarative config, not state

    created_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        server_default=func.now(),
        nullable=False,
        comment="Creation time (UTC), set by the database (Q-08).",
    )
