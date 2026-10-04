"""Import every model here so Alembic autogenerate sees it in Base.metadata."""

from giftmanager.models.base import Base, TimestampMixin
from giftmanager.models.person import Person
from giftmanager.models.user import User, UserSession, UserStatus

__all__ = ["Base", "Person", "TimestampMixin", "User", "UserSession", "UserStatus"]
