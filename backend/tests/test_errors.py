from collections.abc import AsyncIterator

import pytest
from httpx import ASGITransport, AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.db import get_session
from giftmanager.main import app


@pytest.mark.requirement("Q-06")
async def test_unhandled_error_uses_problem_details() -> None:
    # Stands in for a database outage: the session dependency itself fails.
    async def _broken() -> AsyncIterator[AsyncSession]:
        raise ConnectionRefusedError("database is down")
        yield  # pragma: no cover - makes this a generator like get_session

    app.dependency_overrides[get_session] = _broken
    transport = ASGITransport(app=app, raise_app_exceptions=False)
    try:
        async with AsyncClient(transport=transport, base_url="http://test") as client:
            r = await client.get("/api/v1/auth/me", cookies={"session": "anything"})
    finally:
        app.dependency_overrides.clear()

    assert r.status_code == 500
    assert r.json() == {
        "type": "about:blank",
        "title": "Internal Server Error",
        "status": 500,
        "detail": "Unexpected server error",
    }
    assert "database is down" not in r.text
