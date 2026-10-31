"""Planned and sent e-mail notifications (F-13)."""

import enum
import uuid
from datetime import date, datetime

from sqlalchemy import Date, DateTime, Enum, ForeignKey, Index, String, Text, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from giftmanager.models.base import Base, TimestampMixin


class NotificationType(enum.StrEnum):
    """Kind of message."""

    # The collective mail. Reminders 14 days before a birthday are OCCASION with a person reference.
    BIRTHDAY = "birthday"
    CHRISTMAS = "christmas"
    EASTER = "easter"
    OCCASION = "occasion"


class NotificationStatus(enum.StrEnum):
    """Delivery state of a notification."""

    PLANNED = "planned"
    SENDING = "sending"
    SENT = "sent"
    FAILED = "failed"


class ReferenceType(enum.StrEnum):
    """Table that `reference_id` points into."""

    PERSON = "person"
    OCCASION = "occasion"


def _enum_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persist enum VALUES ("planned"), not member names ("PLANNED")."""
    return [str(member.value) for member in enum_cls]


class Notification(TimestampMixin, Base):
    """One planned e-mail. `dedup_key` makes repeated or parallel planner runs harmless."""

    __tablename__ = "notification"
    __table_args__ = (
        Index("ix_notification_status_scheduled_for", "status", "scheduled_for"),
        {
            "comment": "Planned and sent e-mail notifications (F-13). One row per planned "
            "message; dedup_key makes repeated or parallel scheduler runs harmless (Q-02)."
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid7, comment="Primary key, UUIDv7."
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        index=True,
        comment="Account that receives the message. Deleted together with the account.",
    )
    type: Mapped[NotificationType] = mapped_column(
        Enum(
            NotificationType,
            name="notification_type",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=_enum_values,
        ),
        comment="`birthday`, `christmas`, `easter` or `occasion`.",
    )
    reference_type: Mapped[ReferenceType | None] = mapped_column(
        Enum(
            ReferenceType,
            name="notification_reference_type",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=_enum_values,
        ),
        comment="Table that reference_id points into: `person` or `occasion`. NULL without a reference.",
    )
    # No FK: the target table depends on reference_type.
    reference_id: Mapped[uuid.UUID | None] = mapped_column(
        Uuid, comment="Row the message is about. Not a foreign key; see reference_type."
    )
    event_date: Mapped[date] = mapped_column(
        Date, comment="Calendar date of the event the message is about."
    )
    scheduled_for: Mapped[datetime] = mapped_column(
        DateTime(timezone=True), comment="Earliest send time (UTC)."
    )
    expires_at: Mapped[datetime] = mapped_column(
        DateTime(timezone=True),
        comment="Send deadline (UTC). Later than this the message is stale.",
    )
    status: Mapped[NotificationStatus] = mapped_column(
        Enum(
            NotificationStatus,
            name="notification_status",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=_enum_values,
        ),
        default=NotificationStatus.PLANNED,
        server_default=NotificationStatus.PLANNED.value,
        comment="`planned`, `sending`, `sent` or `failed`.",
    )
    claimed_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="When a dispatcher claimed the row for sending (UTC)."
    )
    sent_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True), comment="When the message was handed to the mail server (UTC)."
    )
    error: Mapped[str | None] = mapped_column(Text, comment="Reason of the last failure.")
    dedup_key: Mapped[str] = mapped_column(
        String(255),
        unique=True,
        comment="Identifies the message across planner runs. Unique, so it is never planned twice (Q-02).",
    )
    recipient: Mapped[str] = mapped_column(String(320), comment="Recipient e-mail address.")
    subject: Mapped[str] = mapped_column(String(200), comment="Subject line.")
    body: Mapped[str] = mapped_column(Text, comment="Plain-text message body.")
