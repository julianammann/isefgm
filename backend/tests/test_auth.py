from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

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
    assert "session" in r.cookies
    assert "HttpOnly" in r.headers["set-cookie"]

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
    assert "session" not in wrong.cookies

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
async def test_logout_revokes_the_session(client: AsyncClient, session: AsyncSession) -> None:
    await client.post(REGISTER, json=ANNA)
    token = client.cookies["session"]

    r = await client.post(LOGOUT)
    assert r.status_code == 204
    assert (await client.get(ME)).status_code == 401
    # The cookie is gone client-side and the row is gone server-side.
    client.cookies.set("session", token)
    assert (await client.get(ME)).status_code == 401
    assert await session.scalar(select(func.count()).select_from(UserSession)) == 0


@pytest.mark.requirement("F-01", "Q-03")
async def test_logout_all_revokes_every_session_of_the_user(
    client: AsyncClient, session: AsyncSession
) -> None:
    await client.post(REGISTER, json=ANNA)
    other_device = client.cookies["session"]
    await client.post(LOGIN, json=ANNA_LOGIN)

    r = await client.post(LOGOUT_ALL)
    assert r.status_code == 204
    assert (await client.get(ME)).status_code == 401
    client.cookies.set("session", other_device)
    assert (await client.get(ME)).status_code == 401
    assert await session.scalar(select(func.count()).select_from(UserSession)) == 0


@pytest.mark.requirement("Q-01", "Q-03")
async def test_logout_all_leaves_other_users_logged_in(client: AsyncClient) -> None:
    await client.post(REGISTER, json=BOB)
    bob = client.cookies["session"]
    await client.post(REGISTER, json=ANNA)

    assert (await client.post(LOGOUT_ALL)).status_code == 204
    client.cookies.set("session", bob)
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
    bob = hash_session_token(client.cookies["session"])
    await client.post(REGISTER, json=ANNA)
    expired = hash_session_token(client.cookies["session"])
    await client.post(LOGIN, json=ANNA_LOGIN)
    too_old = hash_session_token(client.cookies["session"])
    await client.post(LOGIN, json=ANNA_LOGIN)
    alive = hash_session_token(client.cookies["session"])

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
    assert remaining == {bob, alive, hash_session_token(client.cookies["session"])}


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
