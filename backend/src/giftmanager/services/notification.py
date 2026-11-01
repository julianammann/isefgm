"""Planning and dispatch of notification mails (F-13)."""

import logging
from collections.abc import Iterable
from dataclasses import dataclass
from datetime import UTC, date, datetime, time, timedelta
from uuid import UUID
from zoneinfo import ZoneInfo

from sqlalchemy import case, select, update
from sqlalchemy.dialects.postgresql import insert
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker

from giftmanager.core.clock import Clock
from giftmanager.core.config import get_settings
from giftmanager.core.mail import Mail, Mailer, MailError, MailFailure, is_reserved_address
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
STUCK_AFTER = timedelta(minutes=15)


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
    # shortcut: one INSERT per call, asyncpg caps bind params at 32767 (~2,500
    # rows); chunk if a single run ever plans more.
    result = await session.execute(
        insert(Notification)
        .values(rows)
        .on_conflict_do_nothing(index_elements=["dedup_key"])
        .returning(Notification.id)
    )
    return len(result.all())


async def claim_next(session: AsyncSession, now: datetime) -> Notification | None:
    """Lock the oldest due `planned` row, skipping rows other dispatchers hold, and mark it `sending`."""
    notification = await session.scalar(
        select(Notification)
        .where(
            Notification.status == NotificationStatus.PLANNED,
            Notification.scheduled_for <= now,
            Notification.expires_at > now,
        )
        # Never-tried rows first, so a row retried after a transient failure cannot block the rest.
        .order_by(
            Notification.claimed_at.asc().nulls_first(), Notification.scheduled_for, Notification.id
        )
        .limit(1)
        .with_for_update(skip_locked=True)
    )
    if notification is not None:
        notification.status = NotificationStatus.SENDING
        notification.claimed_at = now
    return notification


async def dispatch_due(
    sessionmaker: async_sessionmaker[AsyncSession], mailer: Mailer, clock: Clock
) -> int:
    """Send every due mail once and record the outcome; returns the number sent.

    Claim and outcome are separate transactions so no row lock is held while sending.
    A transient failure puts the row back to `planned` and ends the run.
    """
    sent = 0
    while True:
        async with sessionmaker() as session, session.begin():
            claimed = await claim_next(session, clock.now())
            if claimed is None:
                return sent
            notification_id = claimed.id
            # shortcut: subject and body are fixed when planned, so a retry after a transient
            # failure can still name a person deleted since; render at send time if that matters.
            mail = Mail(to=claimed.recipient, subject=claimed.subject, body=claimed.body)

        failure: MailError | None = None
        try:
            await mailer.send(mail)
        except MailError as exc:
            failure = exc

        async with sessionmaker() as session, session.begin():
            notification = await session.get(Notification, notification_id)
            # None: the account was deleted while sending and ON DELETE CASCADE took the row.
            if notification is None:
                if failure is None:
                    sent += 1
                continue
            # No `status == sending` guard: a late TRANSIENT means nothing was delivered, so a retry
            # is a first delivery; a late success correctly overwrites `failed`.
            if failure is None:
                notification.status = NotificationStatus.SENT
                notification.sent_at = clock.now()
                notification.error = None
                sent += 1
            elif failure.failure is MailFailure.TRANSIENT:
                notification.status = NotificationStatus.PLANNED
                notification.error = failure.detail
                logger.warning("Notification %s not sent (transient), will retry", notification_id)
                return sent
            elif failure.failure is MailFailure.PERMANENT:
                notification.status = NotificationStatus.FAILED
                notification.error = failure.detail
                logger.warning("Notification %s not sent (permanent)", notification_id)
            else:
                notification.status = NotificationStatus.FAILED
                notification.error = "Versandergebnis unklar: " + failure.detail
                logger.warning("Delivery result of notification %s is unclear", notification_id)


async def expire(session: AsyncSession, now: datetime) -> int:
    """Fail `planned` rows whose send window has passed; they are never sent late."""
    result = await session.execute(
        update(Notification)
        .where(Notification.status == NotificationStatus.PLANNED, Notification.expires_at <= now)
        .values(status=NotificationStatus.FAILED, error="Zeitfenster abgelaufen")
        .returning(Notification.id)
        .execution_options(synchronize_session="fetch")
    )
    return len(result.all())


async def fail_stuck(session: AsyncSession, now: datetime) -> int:
    """Fail `sending` rows claimed at least STUCK_AFTER ago. The send outcome is unknown, so they are never resent."""
    stuck = (
        await session.execute(
            select(Notification.id, Notification.claimed_at)
            .where(
                Notification.status == NotificationStatus.SENDING,
                Notification.claimed_at <= now - STUCK_AFTER,
            )
            .with_for_update(skip_locked=True)
        )
    ).all()
    if not stuck:
        return 0
    errors: dict[UUID, str] = {}
    for notification_id, claimed_at in stuck:
        if claimed_at is None:  # excluded by the WHERE clause; only for the type checker
            continue
        errors[notification_id] = "Versandergebnis unklar: hängt seit " + claimed_at.isoformat()
        logger.warning("Notification %s stuck in sending; marked failed", notification_id)
    await session.execute(
        update(Notification)
        .where(Notification.id.in_(list(errors)))
        .values(status=NotificationStatus.FAILED, error=case(errors, value=Notification.id))
        .execution_options(synchronize_session="fetch")
    )
    return len(errors)
