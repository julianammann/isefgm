"""create person"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "549db37c1c6e"
down_revision: str | Sequence[str] | None = "8c4f215ecfae"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "person",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Primary key, UUIDv7."),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            nullable=False,
            comment="Account the person belongs to. Deleted together with the account.",
        ),
        sa.Column(
            "name",
            sa.String(length=100),
            nullable=False,
            comment="Name as the owner calls the person.",
        ),
        sa.Column(
            "birthday",
            sa.Date(),
            nullable=True,
            comment="Birthday as a plain date, optional. Source for birthday reminders.",
        ),
        sa.Column(
            "relationship",
            sa.String(length=100),
            nullable=True,
            comment="Free-text relationship, e.g. sister or colleague. Optional.",
        ),
        sa.Column(
            "notes",
            sa.Text(),
            nullable=True,
            comment="Free-text notes, e.g. hobbies or sizes. Optional.",
        ),
        sa.Column(
            "created_at",
            sa.DateTime(timezone=True),
            server_default=sa.text("now()"),
            nullable=False,
            comment="Creation time (UTC), set by the database (Q-08).",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["user_account.id"],
            name=op.f("fk_person_owner_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_person")),
        comment="Person the account owner gives gifts to (F-02). Visible only to its owner (Q-01); deleted together with the account (F-17).",
    )
    op.create_index("ix_person_owner_id_birthday", "person", ["owner_id", "birthday"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index("ix_person_owner_id_birthday", table_name="person")
    op.drop_table("person")
