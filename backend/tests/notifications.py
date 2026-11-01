"""Helpers for notification tests."""

from datetime import UTC, date, datetime
from typing import Any
from uuid import UUID, uuid4

from sqlalchemy import select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from giftmanager.models import User
from giftmanager.models.notification import Notification, NotificationStatus, NotificationType
from giftmanager.services.notification import PlannedMail


async def make_user(session: AsyncSession, email: str) -> User:
    user = User(email=email, password_hash="not-a-real-hash", display_name=email)
    session.add(user)
    await session.flush()
    return user


async def make_committed_user(maker: async_sessionmaker[AsyncSession]) -> User:
    """Account that is really committed, so parallel sessions can see it."""
    async with maker() as s, s.begin():
        return await make_user(s, f"{uuid4()}@committed.isefgm.localhost")


def make_notification(
    user: User,
    *,
    dedup_key: str,
    status: NotificationStatus = NotificationStatus.PLANNED,
    scheduled_for: datetime = datetime(2026, 11, 12, 7, 0, tzinfo=UTC),
    expires_at: datetime = datetime(2026, 11, 16, 7, 0, tzinfo=UTC),
) -> Notification:
    return Notification(
        owner_id=user.id,
        type=NotificationType.CHRISTMAS,
        event_date=date(2026, 12, 24),
        scheduled_for=scheduled_for,
        expires_at=expires_at,
        status=status,
        dedup_key=dedup_key,
        recipient=user.email,
        subject="Betreff",
        body="Text",
    )


def planned_mail(**overrides: object) -> PlannedMail:
    values: dict[str, object] = {
        "owner_id": UUID(int=1),
        "recipient": "konto@isefgm.localhost",
        "type": NotificationType.CHRISTMAS,
        "reference_type": None,
        "reference_id": None,
        "event_date": date(2026, 12, 24),
        "interval": "2026-11-12",
        "scheduled_for": datetime(2026, 11, 12, 7, 0, tzinfo=UTC),
        "expires_at": datetime(2026, 11, 16, 7, 0, tzinfo=UTC),
        "subject": "Betreff",
        "body": "Text",
    }
    return PlannedMail(**{**values, **overrides})  # type: ignore[arg-type]


async def add_committed_notification(
    maker: async_sessionmaker[AsyncSession], **overrides: Any
) -> Notification:
    """Committed account plus one committed notification row."""
    user = await make_committed_user(maker)
    overrides.setdefault("dedup_key", str(uuid4()))
    async with maker() as s, s.begin():
        row = make_notification(user, **overrides)
        s.add(row)
        await s.flush()
        s.expunge(row)
    return row


async def reload(maker: async_sessionmaker[AsyncSession], id: UUID) -> Notification:
    async with maker() as s:
        return await s.get_one(Notification, id)


async def statuses_of(maker: async_sessionmaker[AsyncSession]) -> list[NotificationStatus]:
    async with maker() as s:
        return list(await s.scalars(select(Notification.status).order_by(Notification.dedup_key)))
