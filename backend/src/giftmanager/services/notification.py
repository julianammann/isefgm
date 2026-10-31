"""Send-time, dedup-key and text helpers for notifications (F-13)."""

from dataclasses import dataclass
from datetime import UTC, date, datetime, time
from uuid import UUID
from zoneinfo import ZoneInfo

from giftmanager.core.config import get_settings
from giftmanager.models.gifting import GiftingStatus
from giftmanager.models.notification import NotificationType, ReferenceType

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
