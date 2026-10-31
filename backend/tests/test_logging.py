import logging
import uuid
from collections.abc import Iterator

import pytest
import structlog
from httpx import AsyncClient

from giftmanager.core.logging import configure_logging

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


@pytest.fixture
def restore_logging() -> Iterator[None]:
    root = logging.getLogger()
    handlers, level = list(root.handlers), root.level
    config = structlog.get_config().copy()
    yield
    root.handlers[:] = handlers
    root.setLevel(level)
    structlog.configure(**config)


@pytest.mark.requirement("Q-03")
def test_console_traceback_hides_locals(
    capsys: pytest.CaptureFixture[str], restore_logging: None
) -> None:
    def fail() -> None:
        # Built at runtime: traceback source lines are shown too, only locals could leak it.
        password = "s3cret-" + "marker"  # noqa: F841  # pyright: ignore[reportUnusedVariable]
        raise RuntimeError("login failed")

    configure_logging("INFO", json=False)
    try:
        fail()
    except RuntimeError:
        logging.getLogger("t").exception("send failed")
    out = capsys.readouterr().out
    assert "login failed" in out
    assert "s3cret-marker" not in out
    # Captured stdout is not a TTY, so no ANSI colour codes either.
    assert "\x1b[" not in out
