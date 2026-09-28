"""Account endpoints: register, log in, log out (everywhere), current account, delete account."""

from fastapi import APIRouter, HTTPException, Request, Response, status

from giftmanager.core.auth import (
    CurrentUser,
    clear_session_cookie,
    session_cookie_name,
    set_session_cookie,
)
from giftmanager.core.clock import ClockDep
from giftmanager.core.config import get_settings
from giftmanager.core.db import SessionDep
from giftmanager.schemas.auth import LoginIn, RegisterIn, UserOut
from giftmanager.schemas.common import problem_responses
from giftmanager.services import auth as auth_service

# `summary` (one line) and `description` (behaviour a caller must know) are the
# interface documentation for MS 4; export_docs.py renders them.
router = APIRouter(prefix="/auth", tags=["auth"])


@router.post(
    "/register",
    status_code=status.HTTP_201_CREATED,
    operation_id="authRegister",
    summary="Create account",
    description="Creates an account and logs it in right away: the response sets the "
    "session cookie. The e-mail address is stored lowercased; "
    "an address that is already registered returns 409. When too many logins and "
    "registrations are already being checked, returns 503 at once with a Retry-After "
    "header; retry a few seconds later.",
    responses=problem_responses(409, 503),
)
async def register(
    body: RegisterIn, response: Response, session: SessionDep, clock: ClockDep
) -> UserOut:
    """Create an account and log it in immediately.

    Raises:
        ConflictError: The e-mail address is already registered (409).
        ServiceUnavailableError: Too many password checks are already running (503).
    """
    settings = get_settings()
    user = await auth_service.register(
        session, email=body.email, password=body.password, display_name=body.display_name
    )
    token = await auth_service.create_session(
        session,
        user,
        now=clock.now(),
        ttl=settings.session_ttl,
        max_lifetime=settings.session_max_lifetime,
    )
    set_session_cookie(response, token, settings)
    return UserOut.model_validate(user)


@router.post(
    "/login",
    operation_id="authLogin",
    summary="Log in",
    description="Checks e-mail and password and sets the session cookie on success. "
    "Wrong credentials and unknown addresses get the same 401 response in the same time. "
    "When too many logins and registrations are already being checked, returns 503 at "
    "once with a Retry-After header; retry a few seconds later.",
    responses=problem_responses(401, 503),
)
async def login(body: LoginIn, response: Response, session: SessionDep, clock: ClockDep) -> UserOut:
    """Verify the credentials and set the session cookie.

    Raises:
        HTTPException: 401, identical for wrong passwords and unknown addresses.
        ServiceUnavailableError: Too many password checks are already running (503).
    """
    settings = get_settings()
    user = await auth_service.authenticate(session, email=body.email, password=body.password)
    if user is None:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Invalid e-mail or password")
    token = await auth_service.create_session(
        session,
        user,
        now=clock.now(),
        ttl=settings.session_ttl,
        max_lifetime=settings.session_max_lifetime,
    )
    set_session_cookie(response, token, settings)
    return UserOut.model_validate(user)


@router.post(
    "/logout",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="authLogout",
    summary="Log out",
    description="Revokes the session on the server and clears the cookie. "
    "Idempotent: also works without a cookie or with one that is no longer valid.",
)
async def logout(request: Request, response: Response, session: SessionDep) -> None:
    """Revoke the current session, if any, and clear the cookie. Idempotent."""
    settings = get_settings()
    token = request.cookies.get(session_cookie_name(settings))
    if token:
        await auth_service.revoke_session(session, token)
    clear_session_cookie(response, settings)


@router.post(
    "/logout-all",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="authLogoutAll",
    summary="Log out everywhere",
    description="Revokes every session of the account on every device, this one "
    "included, and clears the cookie. For a lost device or a cookie that may have "
    "been stolen.",
    responses=problem_responses(401),
)
async def logout_all(user: CurrentUser, response: Response, session: SessionDep) -> None:
    """Revoke every session of the account and clear the cookie."""
    await auth_service.revoke_all_sessions(session, user)
    clear_session_cookie(response, get_settings())


@router.get(
    "/me",
    operation_id="authMe",
    summary="Current account",
    description="Returns the account of the current session. The frontend calls it "
    "on every page request to determine the login state.",
    responses=problem_responses(401),
)
async def me(user: CurrentUser) -> UserOut:
    """Return the account of the current session."""
    return UserOut.model_validate(user)


@router.delete(
    "/account",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="authDeleteAccount",
    summary="Delete account",
    description="Deletes the account with all of its data (F-17) and ends the "
    "session. Cannot be undone.",
    responses=problem_responses(401),
)
async def delete_account(user: CurrentUser, response: Response, session: SessionDep) -> None:
    """Delete the account with all owned data (F-17) and clear the cookie."""
    await auth_service.delete_account(session, user)
    clear_session_cookie(response, get_settings())
