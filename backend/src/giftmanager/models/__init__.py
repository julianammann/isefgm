"""Import every model here so Alembic autogenerate sees it in Base.metadata."""

from giftmanager.models.attachment import Attachment, AttachmentKind
from giftmanager.models.base import Base, TimestampMixin
from giftmanager.models.gift import Gift, GiftCategory, gift_occasion, gift_person
from giftmanager.models.gifting import Gifting, GiftingStatus, gifting_person
from giftmanager.models.note import Note
from giftmanager.models.occasion import (
    BIRTHDAY_TYPE_ID,
    CHRISTMAS_TYPE_ID,
    Occasion,
    OccasionType,
    Recurrence,
    person_occasion,
)
from giftmanager.models.person import Person
from giftmanager.models.user import User, UserSession, UserStatus

__all__ = [
    "BIRTHDAY_TYPE_ID",
    "CHRISTMAS_TYPE_ID",
    "Attachment",
    "AttachmentKind",
    "Base",
    "Gift",
    "GiftCategory",
    "Gifting",
    "GiftingStatus",
    "Note",
    "Occasion",
    "OccasionType",
    "Person",
    "Recurrence",
    "TimestampMixin",
    "User",
    "UserSession",
    "UserStatus",
    "gift_occasion",
    "gift_person",
    "gifting_person",
    "person_occasion",
]
