"""Structured logging via structlog for the app and third-party loggers."""

import logging
import re
import sys
import uuid
from collections.abc import Awaitable, Callable

import structlog
from fastapi import Request, Response

_FOREIGN_LOGGERS = ("uvicorn", "uvicorn.error", "uvicorn.access", "sqlalchemy.engine", "alembic")

# The header is client-controlled and lands in every log line of the request, so only
# plain IDs are reused.
_REQUEST_ID = re.compile(r"[A-Za-z0-9._-]{1,64}")


def configure_logging(level: str, *, json: bool) -> None:
    """Route all logging, including uvicorn, SQLAlchemy and Alembic, through structlog.

    Args:
        level: Minimum log level, e.g. ``"INFO"``.
        json: Emit JSON lines (production, test) instead of coloured console output.
    """
    shared: list[structlog.types.Processor] = [
        structlog.contextvars.merge_contextvars,
        structlog.stdlib.add_logger_name,
        structlog.stdlib.add_log_level,
        structlog.stdlib.PositionalArgumentsFormatter(),
        structlog.processors.TimeStamper(fmt="iso", utc=True),
        structlog.processors.StackInfoRenderer(),
    ]

    final: list[structlog.types.Processor] = [
        structlog.stdlib.ProcessorFormatter.remove_processors_meta
    ]

    if json:
        final += [structlog.processors.format_exc_info, structlog.processors.JSONRenderer()]
    else:
        final += [structlog.dev.ConsoleRenderer(colors=sys.stdout.isatty())]

    structlog.configure(
        processors=[*shared, structlog.stdlib.ProcessorFormatter.wrap_for_formatter],
        wrapper_class=structlog.stdlib.BoundLogger,
        logger_factory=structlog.stdlib.LoggerFactory(),
        cache_logger_on_first_use=True,
    )

    handler = logging.StreamHandler(sys.stdout)
    handler.setFormatter(
        structlog.stdlib.ProcessorFormatter(processors=final, foreign_pre_chain=shared)
    )
    root = logging.getLogger()
    root.handlers.clear()
    root.addHandler(handler)
    root.setLevel(level.upper())

    for name in _FOREIGN_LOGGERS:
        logger = logging.getLogger(name)
        logger.handlers.clear()
        logger.propagate = True


async def request_id_middleware(
    request: Request, call_next: Callable[[Request], Awaitable[Response]]
) -> Response:
    """Bind a request ID to every log line of the request and echo it as `x-request-id`.

    An incoming `x-request-id` header is reused if it matches `[A-Za-z0-9._-]{1,64}`;
    otherwise a random UUID is generated.
    """
    incoming = request.headers.get("x-request-id", "")
    # fullmatch, not ^…$: `$` also matches before a trailing newline.
    request_id = incoming if _REQUEST_ID.fullmatch(incoming) else str(uuid.uuid4())
    structlog.contextvars.clear_contextvars()
    structlog.contextvars.bind_contextvars(
        request_id=request_id, path=request.url.path, method=request.method
    )
    response = await call_next(request)
    response.headers["x-request-id"] = request_id
    return response
