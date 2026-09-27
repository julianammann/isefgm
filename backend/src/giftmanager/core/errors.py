"""Uniform error responses (RFC 9457 style problem details) for every failure path.

The frontend needs exactly one mapper for API errors.
"""

from fastapi import FastAPI, Request
from fastapi.exceptions import RequestValidationError
from fastapi.responses import JSONResponse

# Starlette's class, not FastAPI's subclass: the router raises the Starlette one for
# unknown paths (404) and wrong methods (405), and a handler for the subclass would
# not see those.
from starlette.exceptions import HTTPException

from giftmanager.schemas.common import Problem, ValidationIssue


class DomainError(Exception):
    """Base for business rule violations raised in services."""

    status_code = 400
    title = "Bad Request"

    def __init__(self, detail: str) -> None:
        super().__init__(detail)
        self.detail = detail


class NotFoundError(DomainError):
    """Also used for resources owned by another account (Q-01: never leak existence)."""

    status_code = 404
    title = "Not Found"


class ConflictError(DomainError):
    """A uniqueness rule is violated, e.g. an e-mail address is already registered."""

    status_code = 409
    title = "Conflict"


def problem(
    status: int, title: str, detail: str, errors: list[ValidationIssue] | None = None
) -> JSONResponse:
    """Build a problem-details JSON response."""
    body = Problem(title=title, status=status, detail=detail, errors=errors)
    return JSONResponse(status_code=status, content=body.model_dump(exclude_none=True))


async def _domain_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, DomainError)  # noqa: S101 - handler is registered for this type
    return problem(exc.status_code, exc.title, exc.detail)


async def _http_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, HTTPException)  # noqa: S101
    detail = str(exc.detail)
    response = problem(exc.status_code, detail, detail)
    if exc.headers:
        response.headers.update(exc.headers)
    return response


async def _validation_error(_: Request, exc: Exception) -> JSONResponse:
    assert isinstance(exc, RequestValidationError)  # noqa: S101
    errors = [
        ValidationIssue(loc=[str(p) for p in e["loc"]], msg=e["msg"], type=e["type"])
        for e in exc.errors()
    ]
    return problem(422, "Validation Error", "Request validation failed", errors)


async def _unhandled_error(_: Request, exc: Exception) -> JSONResponse:
    # Starlette re-raises after this handler, so the traceback still reaches the log.
    # The body never contains exception details.
    return problem(500, "Internal Server Error", "Unexpected server error")


def register_exception_handlers(app: FastAPI) -> None:
    """Map every failure to problem details: domain, HTTP, validation and unhandled errors."""
    app.add_exception_handler(DomainError, _domain_error)
    app.add_exception_handler(HTTPException, _http_error)
    app.add_exception_handler(RequestValidationError, _validation_error)
    app.add_exception_handler(Exception, _unhandled_error)
