"""Shared schemas: field types, pagination and the problem-details error body."""

from typing import Annotated, Any

from pydantic import BaseModel, BeforeValidator, Field, StringConstraints


def blank_to_none(value: object) -> object:
    """An empty form field means "not set", not an empty string in the database."""
    if isinstance(value, str) and not value.strip():
        return None
    return value


LongText = Annotated[str, StringConstraints(strip_whitespace=True, max_length=2000)]
OptionalLongText = Annotated[LongText | None, BeforeValidator(blank_to_none)]
# Label of a note, link or image (F-07): required, so a list of them stays readable.
Label = Annotated[str, StringConstraints(strip_whitespace=True, min_length=1, max_length=100)]


# Use as `Annotated[PageParams, Query()]` in every list endpoint.
class PageParams(BaseModel):
    """Pagination for list endpoints (Q-05)."""

    limit: int = Field(50, ge=1, le=200)
    offset: int = Field(0, ge=0)


class Page[T](BaseModel):
    """One page of a list, with the total number of items."""

    items: list[T]
    total: int
    limit: int
    offset: int


class ValidationIssue(BaseModel):
    """One invalid field of a request."""

    loc: list[str]
    msg: str
    type: str


class Problem(BaseModel):
    """Error body for every status outside 2xx (RFC 9457)."""

    type: str = "about:blank"
    title: str
    status: int
    detail: str
    errors: list[ValidationIssue] | None = None


# Reusable `responses=` fragments so the OpenAPI schema (and the generated
# TypeScript client) know the error shape.
def problem_responses(*codes: int) -> dict[int | str, dict[str, Any]]:
    """Build a `responses=` mapping that documents the problem-details body for `codes`."""
    return {code: {"model": Problem} for code in codes}
