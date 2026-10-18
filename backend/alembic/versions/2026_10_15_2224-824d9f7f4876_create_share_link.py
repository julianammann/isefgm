"""create share link"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "824d9f7f4876"
down_revision: str | Sequence[str] | None = "5287c5280e97"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "share_link",
        sa.Column("id", sa.Uuid(), nullable=False, comment="Primary key, UUIDv7."),
        sa.Column(
            "owner_id",
            sa.Uuid(),
            nullable=False,
            comment="Account the share link belongs to. Deleted together with the account.",
        ),
        sa.Column(
            "token_hash",
            sa.String(length=64),
            nullable=False,
            comment="SHA-256 of the token in the link. The token itself is shown once and never stored.",
        ),
        sa.Column(
            "active",
            sa.Boolean(),
            server_default=sa.text("true"),
            nullable=False,
            comment="False once the owner deactivates the link; it then no longer opens.",
        ),
        sa.Column(
            "expires_at",
            sa.DateTime(timezone=True),
            nullable=True,
            comment="Expiry time (UTC), optional. The link no longer opens afterwards.",
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
            name=op.f("fk_share_link_owner_id_user_account"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_share_link")),
        sa.UniqueConstraint("token_hash", name=op.f("uq_share_link_token_hash")),
        comment="Read-only share link on chosen people of an account (F-14). Opens only while active and not expired; only the hash of its token is stored (Q-03). Deleted together with the account (F-17).",
    )
    op.create_index(op.f("ix_share_link_owner_id"), "share_link", ["owner_id"], unique=False)
    op.create_table(
        "share_link_person",
        sa.Column(
            "share_link_id",
            sa.Uuid(),
            nullable=False,
            comment="Share link. Deleting it deletes the row.",
        ),
        sa.Column(
            "person_id",
            sa.Uuid(),
            nullable=False,
            comment="Shared person. Deleting the person removes them from the link.",
        ),
        sa.ForeignKeyConstraint(
            ["person_id"],
            ["person.id"],
            name=op.f("fk_share_link_person_person_id_person"),
            ondelete="CASCADE",
        ),
        sa.ForeignKeyConstraint(
            ["share_link_id"],
            ["share_link.id"],
            name=op.f("fk_share_link_person_share_link_id_share_link"),
            ondelete="CASCADE",
        ),
        sa.PrimaryKeyConstraint("share_link_id", "person_id", name=op.f("pk_share_link_person")),
        comment="People whose gift ideas a share link shows (F-14), n:m. Deleting the link or the person removes only the row. Sharing a person does not share their master data.",
    )
    op.create_index(
        op.f("ix_share_link_person_person_id"), "share_link_person", ["person_id"], unique=False
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_share_link_person_person_id"), table_name="share_link_person")
    op.drop_table("share_link_person")
    op.drop_index(op.f("ix_share_link_owner_id"), table_name="share_link")
    op.drop_table("share_link")
