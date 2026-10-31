"""Import every model here so Alembic autogenerate sees it in Base.metadata."""

from giftmanager.models.attachment import Attachment, AttachmentKind
from giftmanager.models.base import Base, TimestampMixin
from giftmanager.models.gift import Gift, GiftCategory, gift_occasion, gift_person
from giftmanager.models.gifting import Gifting, GiftingStatus, gifting_person
from giftmanager.models.note import Note
from giftmanager.models.notification import (
    Notification,
    NotificationStatus,
    NotificationType,
    ReferenceType,
)
from giftmanager.models.occasion import (
    BIRTHDAY_TYPE_ID,
    CHRISTMAS_TYPE_ID,
    Occasion,
    OccasionType,
    Recurrence,
    person_occasion,
)
from giftmanager.models.person import Person
from giftmanager.models.share_link import ShareLink, share_link_person
from giftmanager.models.suggestion import PriceBand, Suggestion, SuggestionStatus
from giftmanager.models.task import Task, TaskStatus
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
    "Notification",
    "NotificationStatus",
    "NotificationType",
    "Occasion",
    "OccasionType",
    "Person",
    "PriceBand",
    "Recurrence",
    "ReferenceType",
    "ShareLink",
    "Suggestion",
    "SuggestionStatus",
    "Task",
    "TaskStatus",
    "TimestampMixin",
    "User",
    "UserSession",
    "UserStatus",
    "gift_occasion",
    "gift_person",
    "gifting_person",
    "person_occasion",
    "share_link_person",
]
