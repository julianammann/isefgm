"""Send-time, dedup-key and text helpers for notifications (F-13)."""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import select
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.config import get_settings
from giftmanager.core.mail import is_reserved_address
from giftmanager.models.gifting import GiftingStatus
from giftmanager.models.notification import (
    Notification,
    NotificationStatus,
    NotificationType,
    ReferenceType,
)
from giftmanager.models.user import User, UserStatus

logger = logging.getLogger(__name__)

SEND_HOUR = 8


def _zone() -> ZoneInfo:
    return ZoneInfo(get_settings().default_timezone)


def local_at(day: date, hour: int = SEND_HOUR) -> datetime:
    """UTC instant of `hour`:00 on `day` in the configured time zone."""
    return datetime.combine(day, time(hour), _zone()).astimezone(UTC)


def local_midnight(day: date) -> datetime:
    """UTC instant of local midnight at the start of `day`."""
    return local_at(day, 0)


def local_date(moment: datetime) -> date:
    """Calendar day of `moment` in the configured time zone."""
    return moment.astimezone(_zone()).date()


@dataclass(frozen=True)
class PlannedMail:
    """One e-mail to send at `scheduled_for`, identified by `dedup_key`."""

    owner_id: UUID
    recipient: str
    type: NotificationType
    reference_type: ReferenceType | None
    reference_id: UUID | None
    event_date: date
    interval: str
    scheduled_for: datetime
    expires_at: datetime
    subject: str
    body: str


def dedup_key(mail: PlannedMail) -> str:
    """Same key for the same mail, so a repeated planner run inserts nothing new."""
    return f"{mail.type}:{mail.owner_id}:{mail.reference_id or '-'}:{mail.event_date.isoformat()}:{mail.interval}"


STATUS_LABELS: dict[GiftingStatus, str] = {
    GiftingStatus.IDEA: "Idee",
    GiftingStatus.PLANNED: "Geplant",
    GiftingStatus.ACQUIRED: "Besorgt",
    GiftingStatus.GIVEN: "Verschenkt",
}


def format_day(day: date) -> str:
    """German day and month for mail texts, e.g. "03.12."."""
    return f"{day.day:02d}.{day.month:02d}."


async def active_recipients(session: AsyncSession) -> list[User]:
    """Active accounts that may receive mail, ordered by id; reserved addresses are skipped."""
    users = await session.scalars(
        select(User).where(User.status == UserStatus.ACTIVE).order_by(User.id)
    )
    recipients: list[User] = []
    for user in users:
        if is_reserved_address(user.email):
            logger.info("Skipping notifications for account %s: reserved address", user.id)
        else:
            recipients.append(user)
    return recipients


async def plan(session: AsyncSession, mails: Iterable[PlannedMail]) -> int:
    """Insert the mails as `planned`; a dedup key that already exists is left alone.

    Returns the number of newly created rows.
    """
    rows = [
        {
            "owner_id": m.owner_id,
            "type": m.type,
            "reference_type": m.reference_type,
            "reference_id": m.reference_id,
            "event_date": m.event_date,
            "scheduled_for": m.scheduled_for,
            "expires_at": m.expires_at,
            "status": NotificationStatus.PLANNED,
            "dedup_key": dedup_key(m),
            "recipient": m.recipient,
            "subject": m.subject,
            "body": m.body,
        }
        for m in mails
    ]
    if not rows:
        return 0
    result = await session.execute(
        insert(Notification)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["dedup_key"])
        .returning(Notification.id)
    )
    return len(result.all())
