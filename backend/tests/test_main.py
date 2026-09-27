from typing import Literal

import pytest
from fastapi import FastAPI
from httpx import ASGITransport, AsyncClient

from giftmanager import main
from giftmanager.core.config import Settings


def _keep_logging(level: str, *, json: bool) -> None:
    """Leave the logging of the test run as it is."""


def _app(monkeypatch: pytest.MonkeyPatch, settings: Settings) -> FastAPI:
    monkeypatch.setattr(main, "get_settings", lambda: settings)
    monkeypatch.setattr(main, "configure_logging", _keep_logging)
    return main.create_app()


@pytest.mark.requirement("Q-03")
@pytest.mark.parametrize(("app_env", "status"), [("development", 200), ("production", 404)])
async def test_schema_and_swagger_ui_are_served_only_in_development(
    monkeypatch: pytest.MonkeyPatch, app_env: Literal["development", "production"], status: int
) -> None:
    app = _app(monkeypatch, Settings(app_env=app_env))
    async with AsyncClient(transport=ASGITransport(app=app), base_url="https://test") as client:
        assert (await client.get("/openapi.json")).status_code == status
        assert (await client.get("/docs")).status_code == status


@pytest.mark.requirement("Q-06", "Q-09")
def test_schema_export_does_not_depend_on_app_env(monkeypatch: pytest.MonkeyPatch) -> None:
    # export_openapi and export_docs call app.openapi(); CI runs them without APP_ENV.
    development = _app(monkeypatch, Settings(app_env="development")).openapi()
    production = _app(monkeypatch, Settings(app_env="production")).openapi()
    assert production == development
    assert "/api/v1/auth/login" in production["paths"]
