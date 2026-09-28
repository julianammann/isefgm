import uuid

import pytest
from httpx import AsyncClient

LIVE = "/api/v1/health/live"


@pytest.mark.requirement("Q-03")
@pytest.mark.parametrize(
    "incoming", ["0b6c1a4e-3f5d-4c1e-9a7b-2d8e6f0a1b3c", "a" * 64], ids=["uuid", "64-chars"]
)
async def test_valid_request_id_is_reused(client: AsyncClient, incoming: str) -> None:
    r = await client.get(LIVE, headers={"x-request-id": incoming})
    assert r.headers["x-request-id"] == incoming


@pytest.mark.requirement("Q-03")
@pytest.mark.parametrize(
    "incoming", ["a" * 65, "two words", '{"level":"error"}'], ids=["too-long", "space", "json"]
)
async def test_invalid_request_id_is_replaced(client: AsyncClient, incoming: str) -> None:
    # The header is client-controlled and lands in every log line of the request.
    r = await client.get(LIVE, headers={"x-request-id": incoming})
    request_id = r.headers["x-request-id"]
    assert request_id != incoming
    assert uuid.UUID(request_id).version == 4
