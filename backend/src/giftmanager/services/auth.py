"""Accounts and server-side sessions (F-01, F-17). No HTTP in here."""

from datetime import datetime, timedelta

from sqlalchemy import delete, or_, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy.orm import selectinload

from giftmanager.core.errors import ConflictError
from giftmanager.core.security import (
    UNKNOWN_USER_HASH,
    admit_password_check,
    hash_password,
    hash_session_token,
    new_session_token,
    verify_password,
)
from giftmanager.models import User, UserSession, UserStatus

# last_seen_at and expires_at are written at most this often to keep reads cheap.
_LAST_SEEN_GRANULARITY = timedelta(minutes=5)


def normalize_email(email: str) -> str:
    """Canonical form of an e-mail address: stripped and lowercased."""
    return email.strip().lower()


async def register(session: AsyncSession, *, email: str, password: str, display_name: str) -> User:
    """Create an account.

    Raises:
        ConflictError: The e-mail address is already registered.
        ServiceUnavailableError: Too many password checks are already running.
    """
    async with admit_password_check():
        password_hash = await hash_password(password)
    user = User(
        email=normalize_email(email),
        password_hash=password_hash,
        display_name=display_name.strip(),
    )
    session.add(user)
    # The unique constraint decides, not a SELECT beforehand: two concurrent
    # registrations would both pass such a check and the second would end in a 500.
    try:
        await session.flush()
    except IntegrityError as exc:
        if "uq_user_account_email" not in str(exc.orig):
            raise
        raise ConflictError("E-mail address is already registered") from exc
    return user


async def authenticate(session: AsyncSession, *, email: str, password: str) -> User | None:
    """Return the active user for the credentials, or None.

    Takes the same time for an unknown address as for a wrong password.

    Raises:
        ServiceUnavailableError: Too many password checks are already running.
    """
    # Before the query: the query checks out a pooled connection, which then waits
    # through the verify.
    async with admit_password_check():
        user = await session.scalar(
            select(User).where(
                User.email == normalize_email(email), User.status == UserStatus.ACTIVE
            )
        )
        if user is None:
            await verify_password(password, UNKNOWN_USER_HASH)
            return None
        return user if await verify_password(password, user.password_hash) else None


async def create_session(
    session: AsyncSession, user: User, *, now: datetime, ttl: timedelta, max_lifetime: timedelta
) -> str:
    """Returns the raw token for the cookie; the database only sees its hash.

    Also deletes the user's sessions that are expired or past `max_lifetime`, so
    the table does not grow without bound.
    """
    await session.execute(
        delete(UserSession).where(
            UserSession.user_id == user.id,
            or_(UserSession.expires_at <= now, UserSession.created_at <= now - max_lifetime),
        )
    )
    token = new_session_token()
    session.add(
        UserSession(
            user_id=user.id,
            token_hash=hash_session_token(token),
            # From the injected clock, not the database default: the absolute
            # lifetime is checked against the same clock.
            created_at=now,
            expires_at=now + min(ttl, max_lifetime),
            last_seen_at=now,
        )
    )
    await session.flush()
    return token


async def user_for_session_token(
    session: AsyncSession, token: str, *, now: datetime, ttl: timedelta, max_lifetime: timedelta
) -> User | None:
    """Return the active user for a valid, unexpired session token, or None.

    Sliding expiry: at most every five minutes, `last_seen_at` is
    refreshed and `expires_at` moves to `now + ttl`, but never past
    `created_at + max_lifetime`. After that the session is rejected, however
    often it is used, so a stolen cookie does not live forever.
    """
    user_session = await session.scalar(
        select(UserSession)
        .where(
            UserSession.token_hash == hash_session_token(token),
            UserSession.expires_at > now,
            UserSession.created_at > now - max_lifetime,
        )
        .options(selectinload(UserSession.user))
    )
    if user_session is None or user_session.user.status != UserStatus.ACTIVE:
        return None
    if now - user_session.last_seen_at >= _LAST_SEEN_GRANULARITY:
        user_session.last_seen_at = now
        user_session.expires_at = min(now + ttl, user_session.created_at + max_lifetime)
    return user_session.user


async def revoke_session(session: AsyncSession, token: str) -> None:
    """Delete the session for the token; a no-op for unknown tokens."""
    await session.execute(
        delete(UserSession).where(UserSession.token_hash == hash_session_token(token))
    )


async def revoke_all_sessions(session: AsyncSession, user: User) -> None:
    """Delete every session of the user on every device, the current one included."""
    await session.execute(delete(UserSession).where(UserSession.user_id == user.id))


async def delete_account(session: AsyncSession, user: User) -> None:
    """F-17: the row goes, every owned row follows via ON DELETE CASCADE."""
    await session.delete(user)
    await session.flush()
