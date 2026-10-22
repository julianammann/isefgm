"""create task"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "4bb3cfa5f0e8"
down_revision: str | Sequence[str] | None = "824d9f7f4876"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "task",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            comment="Primary key, UUIDv7. Orders tasks with the same due date: oldest first.",
        ),
        sa.Column(
            "gifting_id",
            sa.Uuid(),
            nullable=False,
            comment="Gifting the task belongs to. Deleting the gifting deletes the task.",
        ),
        sa.Column(
            "title",
            sa.String(length=200),
            nullable=False,
            comment="What to do, e.g. Karte schreiben.",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "in_progress",
                "done",
                "discarded",
                name="task_status",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            server_default="open",
            nullable=False,
            comment="Progress of the task. Defaults to 'open'.",
        ),
        sa.Column(
            "due_on",
            sa.Date(),
            nullable=True,
            comment="Date. Day the task should be done by (Q-08: plain calendar date, no time zone).",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Creation time (UTC), set by the database (Q-08).",
        ),
        sa.ForeignKeyConstraint(
            ["gifting_id"],
            ["gifting.id"],
            name=op.f("fk_task_gifting_id_gifting"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_task")),
        comment="To-do of a gifting (F-08), already possible in the idea phase. Visible only to the owner of the gift idea (Q-01); deleted together with the gifting and the account (F-17).",
    )
    op.create_index(op.f("ix_task_gifting_id"), "task", ["gifting_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_task_gifting_id"), table_name="task")
    op.drop_table("task")
