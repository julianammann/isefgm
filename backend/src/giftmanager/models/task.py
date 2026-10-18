"""Tasks of a gifting (F-08), e.g. "Netzteil dazu bestellen"."""

import datetime as dt
import enum
import uuid

from sqlalchemy import Enum, ForeignKey, String, Uuid
from sqlalchemy.orm import Mapped, mapped_column

from giftmanager.models.base import Base, TimestampMixin


class TaskStatus(enum.StrEnum):
    """Progress of a task (F-08). Any status may follow any other."""

    OPEN = "open"
    IN_PROGRESS = "in_progress"
    DONE = "done"
    DISCARDED = "discarded"


def _status_values(enum_cls: type[enum.Enum]) -> list[str]:
    """Persist enum value, not member names."""
    return [str(member.value) for member in enum_cls]


class Task(TimestampMixin, Base):
    """To-do of one gifting (F-08). Allowed in every status of the gifting, from `idea` on.

    There is no owner_id: a task belongs to the account of its gifting's gift idea, so every
    query scopes through gift.owner_id (services/task.py), like a gifting.
    """

    __tablename__ = "task"
    __table_args__ = (
        {
            "comment": "To-do of a gifting (F-08), already possible in the idea phase. Visible only "
            "to the owner of the gift idea (Q-01); deleted together with the gifting and the "
            "account (F-17)."
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid,
        primary_key=True,
        default=uuid.uuid7,
        comment="Primary key, UUIDv7. Orders tasks with the same due date: oldest first.",
    )
    gifting_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("gifting.id", ondelete="CASCADE"),
        index=True,
        comment="Gifting the task belongs to. Deleting the gifting deletes the task.",
    )
    title: Mapped[str] = mapped_column(String(200), comment="What to do, e.g. Karte schreiben.")
    status: Mapped[TaskStatus] = mapped_column(
        Enum(
            TaskStatus,
            name="task_status",
            native_enum=False,
            length=16,
            create_constraint=True,
            values_callable=_status_values,
        ),
        default=TaskStatus.OPEN,
        server_default=TaskStatus.OPEN.value,
        comment="Progress of the task. Defaults to 'open'.",
    )
    due_on: Mapped[dt.date | None] = mapped_column(
        comment="Date. Day the task should be done by (Q-08: plain calendar date, no time zone).",
    )
