"""Helpers for notification tests."""

from datetime import UTC, date, datetime

from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import User
from giftmanager.models.notification import Notification, NotificationStatus, NotificationType


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
