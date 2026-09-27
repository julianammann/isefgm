"""Session cookie handling and the `CurrentUser` dependency."""

from typing import Annotated

from fastapi import Depends, HTTPException, Request, Response, status

from giftmanager.core.clock import ClockDep
from giftmanager.core.config import Settings, get_settings
from giftmanager.core.db import SessionDep
from giftmanager.models import User
from giftmanager.services import auth as auth_service

SESSION_COOKIE = "session"


async def get_current_user(
    request: Request, response: Response, session: SessionDep, clock: ClockDep
) -> User:
    """Resolve the logged-in user from the session cookie and renew the cookie.

    Raises:
        HTTPException: 401 if the cookie is missing, unknown or expired.
    """
    settings = get_settings()
    token = request.cookies.get(SESSION_COOKIE)
    user = None
    if token:
        user = await auth_service.user_for_session_token(
            session,
            token,
            now=clock.now(),
            ttl=settings.session_ttl,
            max_lifetime=settings.session_max_lifetime,
        )
    if token is None or user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Not authenticated")
    # Sliding expiry: the browser's Max-Age moves with the server-side
    # expires_at. An endpoint that clears the cookie afterwards still wins, because
    # its Set-Cookie comes later in the response.
    set_session_cookie(response, token, settings)
    return user


# Attach at router level: `APIRouter(dependencies=[Depends(get_current_user)])`, or
# take the user as a parameter where the endpoint needs it.
CurrentUser = Annotated[User, Depends(get_current_user)]


def set_session_cookie(response: Response, token: str, settings: Settings) -> None:
    """Set the HttpOnly session cookie; `Secure` everywhere except development."""
    response.set_cookie(
        SESSION_COOKIE,
        token,
        max_age=int(settings.session_ttl.total_seconds()),
        path="/",
        httponly=True,
        secure=not settings.is_dev,
        samesite="lax",
    )


def clear_session_cookie(response: Response, settings: Settings) -> None:
    """Delete the session cookie with the attributes it was set with."""
    response.delete_cookie(
        SESSION_COOKIE, path="/", httponly=True, secure=not settings.is_dev, samesite="lax"
    )
