from datetime import UTC, datetime, timedelta

from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import User
from giftmanager.services import auth as auth_service

COOKIE = "__Host-session"


async def log_in_new_user(client: AsyncClient, session: AsyncSession, email: str) -> User:
    """Create an account directly and put its session cookie on the client."""
    user = User(email=email, password_hash="not-a-real-hash", display_name=email)
    session.add(user)
    await session.flush()
    token = await auth_service.create_session(
        session,
        user,
        now=datetime.now(UTC),
        ttl=timedelta(hours=1),
        max_lifetime=timedelta(days=1),
    )
    client.cookies.clear()
    client.cookies.set(COOKIE, token)
    return user
