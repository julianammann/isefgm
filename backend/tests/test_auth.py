from datetime import UTC, datetime, timedelta

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select, update
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import UserSession

REGISTER = "/api/v1/auth/register"
LOGIN = "/api/v1/auth/login"
LOGOUT = "/api/v1/auth/logout"
ME = "/api/v1/auth/me"
ACCOUNT = "/api/v1/auth/account"

ANNA = {"email": "Anna@Example.org", "password": "correct-horse-battery", "display_name": "Anna"}


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
