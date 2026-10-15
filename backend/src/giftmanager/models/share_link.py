"""Read-only share links on chosen people (F-14)."""

import uuid
from datetime import datetime

from sqlalchemy import Boolean, Column, DateTime, ForeignKey, String, Table, Uuid, func, true
from sqlalchemy.orm import Mapped, mapped_column, relationship

from giftmanager.models.base import Base, TimestampMixin
from giftmanager.models.person import Person

share_link_person = Table(
    "share_link_person",
    Base.metadata,
    Column(
        "share_link_id",
        Uuid(),
        ForeignKey("share_link.id", ondelete="CASCADE"),
        primary_key=True,
        comment="Share link. Deleting it deletes the row.",
    ),
    Column(
        "person_id",
        Uuid(),
        ForeignKey("person.id", ondelete="CASCADE"),
        primary_key=True,
        index=True,
        comment="Shared person. Deleting the person removes them from the link.",
    ),
    comment="People whose gift ideas a share link shows (F-14), n:m. Deleting the link or the "
    "person removes only the row. Sharing a person does not share their master data.",
)


class ShareLink(TimestampMixin, Base):
    """Read-only link on some of the account's people (F-14). Owned by one account (Q-01)."""

    __tablename__ = "share_link"
    __table_args__ = (
        {
            "comment": "Read-only share link on chosen people of an account (F-14). Opens only "
            "while active and not expired; only the hash of its token is stored (Q-03). "
            "Deleted together with the account (F-17)."
        },
    )

    id: Mapped[uuid.UUID] = mapped_column(
        Uuid, primary_key=True, default=uuid.uuid7, comment="Primary key, UUIDv7."
    )
    owner_id: Mapped[uuid.UUID] = mapped_column(
        ForeignKey("user_account.id", ondelete="CASCADE"),
        index=True,
        comment="Account the share link belongs to. Deleted together with the account.",
    )
    token_hash: Mapped[str] = mapped_column(
        String(64),
        unique=True,
        comment="SHA-256 of the token in the link. The token itself is shown once and never "
        "stored.",
    )
    active: Mapped[bool] = mapped_column(
        Boolean,
        default=True,
        server_default=true(),
        comment="False once the owner deactivates the link; it then no longer opens.",
    )
    expires_at: Mapped[datetime | None] = mapped_column(
        DateTime(timezone=True),
        comment="Expiry time (UTC), optional. The link no longer opens afterwards.",
    )

    people: Mapped[list[Person]] = relationship(
        secondary=share_link_person,
        order_by=lambda: [func.lower(Person.name), Person.id],
        lazy="selectin",
    )
