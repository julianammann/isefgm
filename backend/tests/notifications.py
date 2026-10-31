"""Helpers for notification tests."""

from datetime import UTC, date, datetime
from uuid import UUID

from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import User
from giftmanager.models.notification import Notification, NotificationStatus, NotificationType
from giftmanager.services.notification import PlannedMail


async def make_user(session: AsyncSession, email: str) -> User:
    user = User(email=email, password_hash="not-a-real-hash", display_name=email)
    session.add(user)
    await session.flush()
    return user


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
