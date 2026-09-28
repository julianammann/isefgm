"""Password hashing (Argon2id) and session tokens."""

import hashlib
import secrets
from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from anyio import CapacityLimiter, WouldBlock, to_thread
from pwdlib import PasswordHash

from giftmanager.core.errors import ServiceUnavailableError

# Argon2id via pwdlib's recommended profile.
_password_hash = PasswordHash.recommended()

# Verified against when the e-mail is unknown, so a login attempt takes the same
# time whether or not the account exists.
UNKNOWN_USER_HASH = _password_hash.hash("not-a-real-password")

# Each Argon2id call allocates 64 MiB (m=65536 KiB). anyio's default thread pool would
# run 40 at once; 3 x 64 MiB = 192 MiB leaves room for the app in the api container's
# 512 MiB (compose.production.yaml). Further logins wait instead of OOM-killing it.
_hash_limiter = CapacityLimiter(3)

# A login holds a pooled DB connection while it waits for _hash_limiter, so the wait
# is bounded too: 3 hashing + 8 waiting = 11, the 12th is turned away at once. 11
# admitted requests hold at most 11 of the pool's 15 connections (core/db.py: default
# 5 + 10 overflow), so /auth/me and every other request always keep at least 4.
_admission_limiter = CapacityLimiter(3 + 8)


@asynccontextmanager
async def admit_password_check() -> AsyncGenerator[None]:
    """Hold a password-check slot, or fail at once when all are taken.

    Enter before any database work, so a request that is turned away never holds a
    connection.

    Raises:
        ServiceUnavailableError: 11 checks are already in progress or waiting.
    """
    try:
        _admission_limiter.acquire_nowait()
    except WouldBlock:
        raise ServiceUnavailableError(
            "Too many logins and registrations at once; try again in a few seconds"
        ) from None
    try:
        yield
    finally:
        _admission_limiter.release()


# Argon2id is CPU-bound for tens of milliseconds; both run in a worker thread so a
# login does not stall every other request on the event loop.
async def hash_password(password: str) -> str:
    """Hash a password with Argon2id."""
    return await to_thread.run_sync(_password_hash.hash, password, limiter=_hash_limiter)


async def verify_password(password: str, password_hash: str) -> bool:
    """Check a password against a stored Argon2id hash."""
    return await to_thread.run_sync(
        _password_hash.verify, password, password_hash, limiter=_hash_limiter
    )


def new_session_token() -> str:
    """256 bits of randomness; only its hash is stored."""
    return secrets.token_urlsafe(32)


def hash_session_token(token: str) -> str:
    """SHA-256 hex digest of a session token, as stored in `user_session.token_hash`."""
    return hashlib.sha256(token.encode()).hexdigest()
