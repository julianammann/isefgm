"""Import every model here so Alembic autogenerate sees it in Base.metadata."""

from giftmanager.models.base import Base, TimestampMixin
from giftmanager.models.occasion import (
    BIRTHDAY_TYPE_ID,
    CHRISTMAS_TYPE_ID,
    Occasion,
    OccasionType,
    Recurrence,
)
from giftmanager.models.person import Person
from giftmanager.models.user import User, UserSession, UserStatus

__all__ = [
    "BIRTHDAY_TYPE_ID",
    "CHRISTMAS_TYPE_ID",
    "Base",
    "Occasion",
    "OccasionType",
    "Person",
    "Recurrence",
    "TimestampMixin",
    "User",
    "UserSession",
    "UserStatus",
]
