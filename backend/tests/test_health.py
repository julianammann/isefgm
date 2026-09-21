from httpx import AsyncClient


async def test_live(client: AsyncClient) -> None:
    r = await client.get("/api/v1/health/live")
    assert r.status_code == 200


async def test_ready_hits_database(client: AsyncClient) -> None:
    r = await client.get("/api/v1/health/ready")
    assert r.json() == {"status": "ok", "database": True}
