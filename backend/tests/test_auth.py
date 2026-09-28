from datetime import UTC, datetime, timedelta

import pytest
from anyio import CapacityLimiter
from httpx import AsyncClient, Response
from sqlalchemy import Engine, event, func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core import security
from giftmanager.core.config import get_settings
from giftmanager.core.security import hash_session_token
from giftmanager.models import UserSession
from tests.conftest import FixedClock

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
LOGOUT_ALL = "/api/v1/auth/logout-all"
ME = "/api/v1/auth/me"
ACCOUNT = "/api/v1/auth/account"

# Tests run as APP_ENV=test, where the session cookie is Secure and __Host- prefixed.
COOKIE = "__Host-session"

ANNA = {"email": "Anna@Example.org", "password": "correct-horse-battery", "display_name": "Anna"}
ANNA_LOGIN = {"email": ANNA["email"], "password": ANNA["password"]}
BOB = {"email": "bob@example.org", "password": "correct-horse-battery", "display_name": "Bob"}


@pytest.mark.requirement("F-01")
async def test_register_logs_in_and_normalizes_email(client: AsyncClient) -> None:
    r = await client.post(REGISTER, json=ANNA)
    assert r.status_code == 201
    body = r.json()
    assert body["email"] == "anna@example.org"
    assert body["display_name"] == "Anna"
    assert "password" not in body and "password_hash" not in body
    assert COOKIE in r.cookies
    assert "HttpOnly" in r.headers["set-cookie"]
    assert "Secure" in r.headers["set-cookie"]

    me = await client.get(ME)
    assert me.status_code == 200
    assert me.json()["id"] == body["id"]


@pytest.mark.requirement("F-01")
async def test_register_duplicate_email_is_a_conflict(client: AsyncClient) -> None:
    assert (await client.post(REGISTER, json=ANNA)).status_code == 201
    r = await client.post(REGISTER, json={**ANNA, "email": "anna@example.org"})
    assert r.status_code == 409
    assert r.json()["status"] == 409
    assert r.json()["title"] == "Conflict"


@pytest.mark.requirement("F-01", "Q-03")
async def test_register_validates_password_length(client: AsyncClient) -> None:
    r = await client.post(REGISTER, json={**ANNA, "password": "short"})
    assert r.status_code == 422
    assert r.json()["errors"][0]["loc"] == ["body", "password"]


@pytest.mark.requirement("F-01", "Q-03")
async def test_login_rejects_wrong_password_and_unknown_user(client: AsyncClient) -> None:
    await client.post(REGISTER, json=ANNA)
    client.cookies.clear()

    wrong = await client.post(LOGIN, json={"email": ANNA["email"], "password": "nope-nope-nope"})
    assert wrong.status_code == 401
    assert COOKIE not in wrong.cookies

    unknown = await client.post(
        LOGIN, json={"email": "nobody@example.org", "password": "whatever1"}
    )
    assert unknown.status_code == 401


@pytest.mark.requirement("F-01")
async def test_login_sets_session(client: AsyncClient) -> None:
    await client.post(REGISTER, json=ANNA)
    client.cookies.clear()
    assert (await client.get(ME)).status_code == 401

    r = await client.post(LOGIN, json={"email": ANNA["email"], "password": ANNA["password"]})
    assert r.status_code == 200
    assert (await client.get(ME)).status_code == 200


@pytest.mark.requirement("F-01", "Q-03")
@pytest.mark.parametrize(("path", "body"), [(LOGIN, ANNA_LOGIN), (REGISTER, ANNA)])
async def test_busy_password_checks_are_rejected_before_the_database(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, path: str, body: dict[str, str]
) -> None:
    # Every admission slot is taken, as by a flood of slow logins.
    full = CapacityLimiter(1)
    full.acquire_on_behalf_of_nowait("flood")
    monkeypatch.setattr(security, "_admission_limiter", full)
    statements: list[str] = []

    def _record(_conn: object, _cursor: object, statement: str, *_: object) -> None:
        statements.append(statement)

    event.listen(Engine, "before_cursor_execute", _record)
    try:
        busy = await client.post(path, json=body)
        busy_statements = list(statements)
        full.release_on_behalf_of("flood")
        admitted = await client.post(path, json=body)
    finally:
        event.remove(Engine, "before_cursor_execute", _record)

    assert busy.status_code == 503
    assert busy.headers["retry-after"] == "5"
    assert busy.json() == {
        "type": "about:blank",
        "title": "Service Unavailable",
        "status": 503,
        "detail": "Too many logins and registrations at once; try again in a few seconds",
    }
    assert busy_statements == []
    # The spy does see a request that gets in, so the empty list above is no blind spot.
    assert admitted.status_code != 503
    assert statements


def _set_cookie(r: Response) -> tuple[str, set[str]]:
    """Name and attributes of the single Set-Cookie header of `r`."""
    pair, *attrs = r.headers["set-cookie"].split("; ")
    return pair.split("=", 1)[0], set(attrs)


@pytest.mark.requirement("Q-03")
@pytest.mark.parametrize("app_env", ["test", "production"])
async def test_session_cookie_is_host_prefixed_outside_development(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch, app_env: str
) -> None:
    monkeypatch.setattr(get_settings(), "app_env", app_env)
    register = await client.post(REGISTER, json=ANNA)
    client.cookies.clear()
    login = await client.post(LOGIN, json=ANNA_LOGIN)

    for r in (register, login):
        name, attrs = _set_cookie(r)
        # __Host- makes the browser insist on Secure, Path=/ and no Domain.
        assert name == "__Host-session"
        assert {"HttpOnly", "Path=/", "SameSite=lax", "Secure"} <= attrs
        assert not any(a.lower().startswith("domain=") for a in attrs)

    client.cookies.clear()
    client.cookies.set("__Host-session", login.cookies["__Host-session"])
    assert (await client.get(ME)).status_code == 200


@pytest.mark.requirement("Q-03")
async def test_plain_session_cookie_is_ignored_outside_development(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    monkeypatch.setattr(get_settings(), "app_env", "production")
    await client.post(REGISTER, json=ANNA)
    token = client.cookies["__Host-session"]
    client.cookies.clear()

    # What a sibling subdomain can plant: a valid token under the unprefixed name.
    client.cookies.set("session", token)
    assert (await client.get(ME)).status_code == 401


@pytest.mark.requirement("Q-03")
async def test_session_cookie_is_plain_in_development(
    client: AsyncClient, monkeypatch: pytest.MonkeyPatch
) -> None:
    # Development runs on plain http, and browsers reject a __Host- cookie without Secure.
    monkeypatch.setattr(get_settings(), "app_env", "development")
    r = await client.post(REGISTER, json=ANNA)
    name, attrs = _set_cookie(r)
    assert name == "session"
    assert {"HttpOnly", "Path=/", "SameSite=lax"} <= attrs
    assert "Secure" not in attrs
    assert (await client.get(ME)).status_code == 200

    logout = await client.post(LOGOUT)
    assert _set_cookie(logout)[0] == "session"
    assert "session" not in client.cookies


@pytest.mark.requirement("F-01", "Q-03")
async def test_logout_revokes_the_session(client: AsyncClient, session: AsyncSession) -> None:
    await client.post(REGISTER, json=ANNA)
    token = client.cookies[COOKIE]

    r = await client.post(LOGOUT)
    assert r.status_code == 204
    assert (await client.get(ME)).status_code == 401
    # The cookie is gone client-side and the row is gone server-side.
    client.cookies.set(COOKIE, token)
    assert (await client.get(ME)).status_code == 401
    assert await session.scalar(select(func.count()).select_from(UserSession)) == 0


@pytest.mark.requirement("F-01", "Q-03")
async def test_logout_all_revokes_every_session_of_the_user(
    client: AsyncClient, session: AsyncSession
) -> None:
    await client.post(REGISTER, json=ANNA)
    other_device = client.cookies[COOKIE]
    await client.post(LOGIN, json=ANNA_LOGIN)

    r = await client.post(LOGOUT_ALL)
    assert r.status_code == 204
    assert (await client.get(ME)).status_code == 401
    client.cookies.set(COOKIE, other_device)
    assert (await client.get(ME)).status_code == 401
    assert await session.scalar(select(func.count()).select_from(UserSession)) == 0


@pytest.mark.requirement("Q-01", "Q-03")
async def test_logout_all_leaves_other_users_logged_in(client: AsyncClient) -> None:
    await client.post(REGISTER, json=BOB)
    bob = client.cookies[COOKIE]
    await client.post(REGISTER, json=ANNA)

    assert (await client.post(LOGOUT_ALL)).status_code == 204
    client.cookies.set(COOKIE, bob)
    me = await client.get(ME)
    assert me.status_code == 200
    assert me.json()["email"] == BOB["email"]


@pytest.mark.requirement("Q-01", "Q-03")
async def test_logout_all_without_session_is_unauthorized(client: AsyncClient) -> None:
    r = await client.post(LOGOUT_ALL)
    assert r.status_code == 401
    assert r.json()["status"] == 401


@pytest.mark.requirement("Q-03")
async def test_expired_session_is_rejected(client: AsyncClient, session: AsyncSession) -> None:
    await client.post(REGISTER, json=ANNA)
    await session.execute(
        update(UserSession).values(expires_at=datetime.now(UTC) - timedelta(seconds=1))
    )
    assert (await client.get(ME)).status_code == 401


@pytest.mark.requirement("F-01", "Q-03")
async def test_session_expiry_slides_with_use(client: AsyncClient, session: AsyncSession) -> None:
    await client.post(REGISTER, json=ANNA)
    now = datetime.now(UTC)
    soon = now + timedelta(hours=1)
    await session.execute(
        update(UserSession).values(expires_at=soon, last_seen_at=now - timedelta(minutes=10))
    )

    r = await client.get(ME)
    assert r.status_code == 200
    # Server side and cookie both move to a full TTL (14 days) from now.
    expires_at = await session.scalar(select(UserSession.expires_at))
    assert expires_at is not None
    assert expires_at > now + timedelta(days=13)
    assert "Max-Age=1209600" in r.headers["set-cookie"]


@pytest.mark.requirement("Q-03")
async def test_session_ends_after_max_lifetime_despite_use(
    client: AsyncClient, clock: FixedClock
) -> None:
    await client.post(REGISTER, json=ANNA)
    # Used every day, so sliding expiry alone would keep it alive forever.
    for _ in range(29):
        clock.advance(timedelta(days=1))
        assert (await client.get(ME)).status_code == 200

    clock.advance(timedelta(days=1))
    assert (await client.get(ME)).status_code == 401


@pytest.mark.requirement("Q-03")
async def test_renewal_never_moves_expiry_past_max_lifetime(
    client: AsyncClient, session: AsyncSession, clock: FixedClock
) -> None:
    await client.post(REGISTER, json=ANNA)
    login = clock.now()

    for _ in range(2):
        clock.advance(timedelta(days=10))
        assert (await client.get(ME)).status_code == 200
    # now + 14 days would be day 34; the cap is day 30 after login.
    assert await session.scalar(select(UserSession.expires_at)) == login + timedelta(days=30)


@pytest.mark.requirement("Q-03")
async def test_initial_expiry_respects_max_lifetime(
    client: AsyncClient,
    session: AsyncSession,
    clock: FixedClock,
    monkeypatch: pytest.MonkeyPatch,
) -> None:
    monkeypatch.setattr(get_settings(), "session_ttl_days", 60)
    await client.post(REGISTER, json=ANNA)
    assert await session.scalar(select(UserSession.expires_at)) == clock.now() + timedelta(days=30)


@pytest.mark.requirement("Q-03")
async def test_session_older_than_max_lifetime_is_rejected(
    client: AsyncClient, session: AsyncSession, clock: FixedClock
) -> None:
    await client.post(REGISTER, json=ANNA)
    clock.advance(timedelta(days=30))
    # A row from before the cap existed, or one created under a longer setting:
    # expires_at alone would still let it in.
    await session.execute(update(UserSession).values(expires_at=clock.now() + timedelta(days=1)))
    assert (await client.get(ME)).status_code == 401


@pytest.mark.requirement("Q-03")
async def test_login_purges_the_users_dead_sessions(
    client: AsyncClient, session: AsyncSession, clock: FixedClock
) -> None:
    await client.post(REGISTER, json=BOB)
    bob = hash_session_token(client.cookies[COOKIE])
    await client.post(REGISTER, json=ANNA)
    expired = hash_session_token(client.cookies[COOKIE])
    await client.post(LOGIN, json=ANNA_LOGIN)
    too_old = hash_session_token(client.cookies[COOKIE])
    await client.post(LOGIN, json=ANNA_LOGIN)
    alive = hash_session_token(client.cookies[COOKIE])

    now = clock.now()
    dead_by_expiry = UserSession.token_hash.in_([bob, expired])
    await session.execute(update(UserSession).where(dead_by_expiry).values(expires_at=now))
    await session.execute(
        update(UserSession)
        .where(UserSession.token_hash == too_old)
        .values(created_at=now - timedelta(days=30))
    )

    await client.post(LOGIN, json=ANNA_LOGIN)
    remaining = set(await session.scalars(select(UserSession.token_hash)))
    # Only Anna's dead sessions go: her live one stays, Bob's expired one waits for his login.
    assert remaining == {bob, alive, hash_session_token(client.cookies[COOKIE])}


@pytest.mark.requirement("F-17")
async def test_delete_account_removes_user_and_sessions(
    client: AsyncClient, session: AsyncSession
) -> None:
    await client.post(REGISTER, json=ANNA)

    r = await client.delete(ACCOUNT)
    assert r.status_code == 204
    assert (await client.get(ME)).status_code == 401
    login = await client.post(LOGIN, json={"email": ANNA["email"], "password": ANNA["password"]})
    assert login.status_code == 401
    assert await session.scalar(select(func.count()).select_from(UserSession)) == 0


@pytest.mark.requirement("Q-01", "Q-03")
async def test_me_without_cookie_is_unauthorized(client: AsyncClient) -> None:
    r = await client.get(ME)
    assert r.status_code == 401
    assert r.json() == {
        "type": "about:blank",
        "title": "Not authenticated",
        "status": 401,
        "detail": "Not authenticated",
    }


@pytest.mark.requirement("Q-06")
async def test_unknown_route_and_method_use_problem_details(client: AsyncClient) -> None:
    # Raised by Starlette's router, not by an endpoint (every failure path).
    missing = await client.get("/api/v1/does-not-exist")
    assert missing.status_code == 404
    assert missing.json()["title"] == "Not Found"
    assert missing.json()["status"] == 404

    wrong_method = await client.put(ME)
    assert wrong_method.status_code == 405
    assert wrong_method.json()["status"] == 405
