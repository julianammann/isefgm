"""add image columns to attachment"""

from collections.abc import Sequence
from typing import Union

import sqlalchemy as sa
from alembic import op

revision: str = "6b982e34bd4b"
down_revision: str | Sequence[str] | None = "4bb3cfa5f0e8"
branch_labels: str | Sequence[str] | None = None
depends_on: str | Sequence[str] | None = None


def upgrade() -> None:
    """Upgrade schema."""
    op.add_column(
        "attachment",
        sa.Column(
            "storage_path",
            sa.String(length=255),
            nullable=True,
            comment="Path of the WebP file relative to UPLOADS_DIR, `<owner_id>/<random>.webp`. Required for images, NULL for links.",
        ),
    )
    op.add_column(
        "attachment",
        sa.Column(
            "mime_type",
            sa.String(length=100),
            nullable=True,
            comment="Media type of the stored file, always image/webp. Required for images, NULL for links.",
        ),
    )
    op.add_column(
        "attachment",
        sa.Column(
            "size_bytes",
            sa.Integer(),
            nullable=True,
            comment="Size of the stored file in bytes. Required for images, NULL for links.",
        ),
    )
    op.create_unique_constraint(op.f("uq_attachment_storage_path"), "attachment", ["storage_path"])
    # Autogenerate does not detect check constraints; written by hand like the model's.
    op.create_check_constraint(
        op.f("ck_attachment_image_has_file"),
        "attachment",
        "kind <> 'image' OR (storage_path IS NOT NULL AND mime_type IS NOT NULL "
        "AND size_bytes IS NOT NULL)",
    )


def downgrade() -> None:
    """Downgrade schema."""
    op.drop_constraint(op.f("ck_attachment_image_has_file"), "attachment", type_="check")
    op.drop_constraint(op.f("uq_attachment_storage_path"), "attachment", type_="unique")
    op.drop_column("attachment", "size_bytes")
    op.drop_column("attachment", "mime_type")
    op.drop_column("attachment", "storage_path")
