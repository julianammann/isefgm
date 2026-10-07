"""create occasion type and occasion"""

import uuid
from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "393161257686"
down_revision: str | Sequence[str] | None = "549db37c1c6e"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "occasion_type",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Primary key, UUIDv7."),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            nullable=True,
            comment="Account that defined the type. NULL for system-wide types.",
        ),
        sa.Column(
            "name", sa.String(length=100), nullable=False, comment="Display name, e.g. Geburtstag."
        ),
        sa.Column(
            "default_recurrence",
            sa.Enum(
                "none",
                "yearly",
                name="occasion_type_recurrence",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            server_default="yearly",
            nullable=False,
            comment="`none` or `yearly`. Suggested recurrence for occasions of this type.",
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["user_account.id"],
            name=op.f("fk_occasion_type_owner_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_occasion_type")),
        comment="Kind of occasion (F-03). owner_id NULL marks the system-wide types Geburtstag and Weihnachten, created by a migration and read-only for users.",
    )
    op.create_index(op.f("ix_occasion_type_owner_id"), "occasion_type", ["owner_id"], unique=False)
    occasion_type = sa.table(
        "occasion_type",
        sa.column("id", sa.Uuid()),
        sa.column("owner_id", sa.Uuid()),
        sa.column("name", sa.String()),
        sa.column("default_recurrence", sa.String()),
    )
    op.bulk_insert(
        occasion_type,
        [
            {
                "id": uuid.UUID("01a107a9-211b-7486-a304-d5d673618f5b"),
                "owner_id": None,
                "name": "Geburtstag",
                "default_recurrence": "yearly",
            },
            {
                "id": uuid.UUID("01a107a9-211b-7486-a304-d5d72f070565"),
                "owner_id": None,
                "name": "Weihnachten",
                "default_recurrence": "yearly",
            },
        ],
    )
    op.create_table(
        "occasion",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Primary key, UUIDv7."),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            nullable=False,
            comment="Account the occasion belongs to. Deleted together with the account.",
        ),
        sa.Column(
            "occasion_type_id",
            sa.Uuid(),
            nullable=True,
            comment="Type of the occasion. NULL for an own occasion without a type.",
        ),
        sa.Column(
            "name", sa.String(length=100), nullable=False, comment="Title, e.g. Hochzeitstag."
        ),
        sa.Column(
            "date",
            sa.Date(),
            nullable=False,
            comment="Date as a plain calendar date (Q-08). First occurrence for yearly ones.",
        ),
        sa.Column(
            "recurrence",
            sa.Enum(
                "none",
                "yearly",
                name="occasion_recurrence",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
            comment="`none` (once) or `yearly` (every year on the same day).",
        ),
        sa.ForeignKeyConstraint(
            ["occasion_type_id"],
            ["occasion_type.id"],
            name=op.f("fk_occasion_occasion_type_id_occasion_type"),
        ),
        sa.ForeignKeyConstraint(
            ["owner_id"],
            ["user_account.id"],
            name=op.f("fk_occasion_owner_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_occasion")),
        comment="Occasion of an account (F-03). Stores the rule (date and recurrence); a concrete year is stored where the occasion is used. Visible only to its owner (Q-01).",
    )
    op.create_index(
        op.f("ix_occasion_occasion_type_id"), "occasion", ["occasion_type_id"], unique=False
    )
    op.create_index(op.f("ix_occasion_owner_id"), "occasion", ["owner_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_occasion_owner_id"), table_name="occasion")
    op.drop_index(op.f("ix_occasion_occasion_type_id"), table_name="occasion")
    op.drop_table("occasion")
    op.drop_index(op.f("ix_occasion_type_owner_id"), table_name="occasion_type")
    op.drop_table("occasion_type")
