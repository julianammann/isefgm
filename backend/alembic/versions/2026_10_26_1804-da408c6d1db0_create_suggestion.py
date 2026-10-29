"""create suggestion"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "da408c6d1db0"
down_revision: str | Sequence[str] | None = "6b982e34bd4b"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "suggestion",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Primary key, UUIDv7."),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            nullable=False,
            comment="Account the suggestion belongs to. Deleted together with the account.",
        ),
        sa.Column(
            "target_person_id",
            sa.Uuid(),
            nullable=False,
            comment="Person the suggestion is for. Deleting the person deletes the suggestion.",
        ),
        sa.Column(
            "category",
            sa.Enum(
                "books",
                "games",
                "experience",
                "clothing",
                "tech",
                "food",
                "home",
                "voucher",
                "other",
                name="gift_category",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
            comment="Suggested kind of gift, never `other`.",
        ),
        sa.Column(
            "price_band",
            sa.Enum(
                "under_20",
                "20_to_50",
                "50_to_100",
                "over_100",
                name="price_band",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=True,
            comment="Suggested price band in EUR. Null for ideas without a price in EUR.",
        ),
        sa.Column(
            "gift_count",
            sa.Integer(),
            nullable=False,
            comment="Number of gift ideas of other accounts with this category and price band when the suggestion was made. A count only, no reference to the ideas.",
        ),
        sa.Column(
            "status",
            sa.Enum(
                "open",
                "accepted",
                "dismissed",
                name="suggestion_status",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            server_default="open",
            nullable=False,
            comment="`open`, `accepted` or `dismissed`. A dismissed suggestion is never made again for the person.",
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
            name=op.f("fk_suggestion_owner_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["target_person_id"],
            ["person.id"],
            name=op.f("fk_suggestion_target_person_id_person"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_suggestion")),
        comment="Suggested kind of gift for a person (F-16): category and price band aggregated over the gift ideas of other accounts, no titles or texts (Q-04). Visible only to its owner (Q-01); deleted together with the person and the account (F-17).",
    )
    op.create_index(op.f("ix_suggestion_owner_id"), "suggestion", ["owner_id"], unique=False)
    op.create_index(
        op.f("ix_suggestion_target_person_id"), "suggestion", ["target_person_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_suggestion_target_person_id"), table_name="suggestion")
    op.drop_index(op.f("ix_suggestion_owner_id"), table_name="suggestion")
    op.drop_table("suggestion")
