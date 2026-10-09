"""Tenant separation (Q-01): every read of account-bound rows goes through these helpers.

No HTTP in here. Rules: backend/README.md, section "Mandantentrennung (Q-01)".
"""

import uuid
from collections.abc import Iterable
from typing import Protocol

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import Mapped

from giftmanager.core.errors import NotFoundError


class Owned(Protocol):
    """Model of an account-bound table: UUID primary key `id` and a non-null `owner_id`."""

    # Structural typing instead of a base class or mixin: Person and Occasion match because
    # they declare both attributes, so models and migrations stay untouched (a mixin would
    # change column comments/indexes and `alembic check` would demand a migration).
    # OccasionType does NOT match (owner_id is nullable): pyright rejects it on purpose.
    # https://typing.python.org/en/latest/spec/protocol.html
    id: Mapped[uuid.UUID]
    owner_id: Mapped[uuid.UUID]


def owned[T: Owned](model: type[T], owner_id: uuid.UUID) -> Select[tuple[T]]:
    """Return a SELECT of the owner's rows of `model`; callers add ordering and paging."""
    return select(model).where(model.owner_id == owner_id)


async def get_owned[T: Owned](
    session: AsyncSession, model: type[T], owner_id: uuid.UUID, row_id: uuid.UUID
) -> T:
    """Return the owner's row with this id.

    Raises:
        NotFoundError: The row does not exist or belongs to another account.
    """
    row = await session.scalar(owned(model, owner_id).where(model.id == row_id))
    if row is None:
        raise NotFoundError(f"{model.__name__} not found")

    return row


async def get_all_owned[T: Owned](
    session: AsyncSession, model: type[T], owner_id: uuid.UUID, row_ids: Iterable[uuid.UUID]
) -> list[T]:
    """Return the owner's rows with these ids, e.g. to link them; a repeated id counts once.

    Raises:
        NotFoundError: One of the rows does not exist or belongs to another account.
    """
    wanted = set(row_ids)
    if not wanted:
        return []
    rows = list(await session.scalars(owned(model, owner_id).where(model.id.in_(wanted))))
    if len(rows) != len(wanted):
        raise NotFoundError(f"{model.__name__} not found")

    return rows


async def paginate[T](
    session: AsyncSession, stmt: Select[tuple[T]], *, limit: int, offset: int
) -> tuple[list[T], int]:
    """Return one page of `stmt` and the total number of rows `stmt` matches."""
    total = await session.scalar(select(func.count()).select_from(stmt.order_by(None).subquery()))
    rows = await session.scalars(stmt.limit(limit).offset(offset))
    return list(rows), total or 0
