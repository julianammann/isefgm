"""create note and attachment"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "5287c5280e97"
down_revision: str | Sequence[str] | None = "02a75ea2c1ac"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.create_table(
        "attachment",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            comment="Primary key, UUIDv7. Also the list order: oldest attachment first.",
        ),
        sa.Column(
            "gift_id",
            sa.Uuid(),
            nullable=False,
            comment="Gift idea the attachment belongs to. Deleting the idea deletes it.",
        ),
        sa.Column(
            "kind",
            sa.Enum(
                "link",
                "image",
                name="attachment_kind",
                native_enum=False,
                create_constraint=True,
                length=16,
            ),
            nullable=False,
            comment="`link` or `image`.",
        ),
        sa.Column(
            "label",
            sa.String(length=100),
            nullable=False,
            comment="Label, e.g. Thalia or Bild vom Laden.",
        ),
        sa.Column(
            "url",
            sa.String(length=2048),
            nullable=True,
            comment="Absolute http or https URL. Required for links, NULL for images.",
        ),
        sa.CheckConstraint(
            "kind <> 'link' OR url IS NOT NULL", name=op.f("ck_attachment_link_has_url")
        ),
        sa.ForeignKeyConstraint(
            ["gift_id"], ["gift.id"], name=op.f("fk_attachment_gift_id_gift"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_attachment")),
        comment="Labelled link or image on a gift idea (F-07), told apart by kind. Visible only to the owner of the idea (Q-01); deleted together with the idea and the account (F-17).",
    )
    op.create_index(op.f("ix_attachment_gift_id"), "attachment", ["gift_id"], unique=False)
    op.create_table(
        "note",
        sa.Column(
            "id",
            sa.Uuid(),
            nullable=False,
            comment="Primary key, UUIDv7. Also the list order: oldest note first.",
        ),
        sa.Column(
            "gift_id",
            sa.Uuid(),
            nullable=False,
            comment="Gift idea the note belongs to. Deleting the idea deletes the note.",
        ),
        sa.Column("label", sa.String(length=100), nullable=False, comment="Label, e.g. Größe."),
        sa.Column(
            "text", sa.Text(), nullable=False, comment="Text of the note, up to 2000 characters."
        ),
        sa.ForeignKeyConstraint(
            ["gift_id"], ["gift.id"], name=op.f("fk_note_gift_id_gift"), ondelete="CASCADE"
        ),
        sa.PrimaryKeyConstraint("id", name=op.f("pk_note")),
        comment="Labelled note on a gift idea (F-07). Visible only to the owner of the idea (Q-01); deleted together with the idea and the account (F-17).",
    )
    op.create_index(op.f("ix_note_gift_id"), "note", ["gift_id"], unique=False)


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_index(op.f("ix_note_gift_id"), table_name="note")
    op.drop_table("note")
    op.drop_index(op.f("ix_attachment_gift_id"), table_name="attachment")
    op.drop_table("attachment")
