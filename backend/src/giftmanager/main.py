"""FastAPI application factory and the ASGI app `app`."""

from collections.abc import AsyncGenerator
from contextlib import asynccontextmanager

from fastapi import FastAPI

from giftmanager import __version__
from giftmanager.api.v1.router import router as v1_router
from giftmanager.core.config import get_settings
from giftmanager.core.db import get_engine
from giftmanager.core.errors import register_exception_handlers
from giftmanager.core.logging import configure_logging, request_id_middleware


@asynccontextmanager
async def lifespan(_: FastAPI) -> AsyncGenerator[None]:
    """Dispose of the database engine on shutdown."""
    yield
    await get_engine().dispose()


# One entry per router tag. export_docs.py uses the description as the chapter
# intro in docs/generated/api.md.
OPENAPI_TAGS = [
    {
        "name": "health",
        "description": "Liveness and readiness for container healthchecks and Traefik.",
    },
    {
        "name": "auth",
        "description": "Create, log in to, log out of and delete an account (F-01, F-17). "
        "The session lives on the server; the browser only holds a cookie.",
    },
]


def create_app() -> FastAPI:
    """Build the FastAPI app: logging, middleware, error handlers and routers."""
    settings = get_settings()
    # Configure logging here, not in lifespan: uvicorn startup lines and test runs
    # (ASGITransport skips lifespan) are structured too.
    configure_logging(settings.log_level, json=not settings.is_dev)

    app = FastAPI(
        title=settings.app_name,
        version=__version__,
        lifespan=lifespan,
        openapi_tags=OPENAPI_TAGS,
        # Schema and Swagger UI only in development. app.openapi() still works, so
        # export_openapi and export_docs produce the full schema in every environment.
        openapi_url="/openapi.json" if settings.is_dev else None,
        docs_url="/docs" if settings.is_dev else None,
        redoc_url=None,
    )
    # No CORS middleware: the browser only talks to the SvelteKit origin, which proxies
    # to this API server-side. Add it back only if a second origin appears.
    app.middleware("http")(request_id_middleware)
    register_exception_handlers(app)
    app.include_router(v1_router)
    return app


app = create_app()
