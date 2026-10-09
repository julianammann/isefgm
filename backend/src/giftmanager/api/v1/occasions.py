"""Occasion type and occasion endpoints (F-03).

Create and update also link the occasion to the account's people (F-04).
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from giftmanager.core.auth import CurrentUser
from giftmanager.core.db import SessionDep
from giftmanager.models import OccasionType
from giftmanager.schemas.common import Page, PageParams, problem_responses
from giftmanager.schemas.occasion import OccasionIn, OccasionOut, OccasionTypeOut
from giftmanager.services import occasion as occasion_service

types_router = APIRouter(prefix="/occasion-types", tags=["occasions"])
router = APIRouter(prefix="/occasions", tags=["occasions"])

_NOT_FOUND_NOTE = " An occasion of another account returns 404, like a missing one."
_TYPE_NOTE = (
    " `occasion_type_id` must be a system-wide type or one of the account; otherwise 404."
    " Geburtstag returns 422: birthday occasions come from a person's birthday."
)
_BIRTHDAY_NOTE = " A birthday occasion follows its person and returns 409; edit the person."
_PEOPLE_NOTE = (
    " `person_ids` links the occasion to people of the account; an ID of another account"
    " returns 404, like a missing one, and nothing is saved."
)


def _type_out(occasion_type: OccasionType) -> OccasionTypeOut:
    """Map a type row to its response body."""
    return OccasionTypeOut(
        id=occasion_type.id,
        name=occasion_type.name,
        default_recurrence=occasion_type.default_recurrence,
        system=occasion_type.owner_id is None,
    )


@types_router.get(
    "",
    operation_id="listOccasionTypes",
    summary="List occasion types",
    description="Returns the system-wide types Geburtstag and Weihnachten followed by the "
    "account's own types. System-wide types are read-only: there is no endpoint to change "
    "or delete them.",
    responses=problem_responses(401),
)
async def list_occasion_types(
    user: CurrentUser, session: SessionDep, page: Annotated[PageParams, Query()]
) -> Page[OccasionTypeOut]:
    """Return one page of the occasion types the current account can use."""
    types, total = await occasion_service.list_occasion_types(
        session, user.id, limit=page.limit, offset=page.offset
    )
    return Page[OccasionTypeOut](
        items=[_type_out(t) for t in types], total=total, limit=page.limit, offset=page.offset
    )


@types_router.get(
    "/{occasion_type_id}",
    operation_id="getOccasionType",
    summary="Show occasion type",
    description="Returns one system-wide type or one of the account's own types. A type of "
    "another account returns 404.",
    responses=problem_responses(401, 404),
)
async def get_occasion_type(
    occasion_type_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> OccasionTypeOut:
    """Return one occasion type."""
    occasion_type = await occasion_service.get_occasion_type(session, user.id, occasion_type_id)
    return _type_out(occasion_type)


@router.get(
    "",
    operation_id="listOccasions",
    summary="List occasions",
    description="Returns the occasions of the current account, sorted by date, one page at "
    "a time. `total` counts all occasions of the account.",
    responses=problem_responses(401),
)
async def list_occasions(
    user: CurrentUser, session: SessionDep, page: Annotated[PageParams, Query()]
) -> Page[OccasionOut]:
    """Return one page of the current account's occasions."""
    occasions, total = await occasion_service.list_occasions(
        session, user.id, limit=page.limit, offset=page.offset
    )
    return Page[OccasionOut](
        items=[OccasionOut.model_validate(o) for o in occasions],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    operation_id="createOccasion",
    summary="Create occasion",
    description="Creates a one-off or yearly occasion for the current account."
    + _TYPE_NOTE
    + _PEOPLE_NOTE,
    responses=problem_responses(401, 404),
)
async def create_occasion(body: OccasionIn, user: CurrentUser, session: SessionDep) -> OccasionOut:
    """Create an occasion for the current account."""
    occasion = await occasion_service.create_occasion(session, user.id, **body.model_dump())
    return OccasionOut.model_validate(occasion)


@router.get(
    "/{occasion_id}",
    operation_id="getOccasion",
    summary="Show occasion",
    description="Returns one occasion of the current account." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def get_occasion(
    occasion_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> OccasionOut:
    """Return one occasion of the current account."""
    occasion = await occasion_service.get_occasion(session, user.id, occasion_id)
    return OccasionOut.model_validate(occasion)


@router.put(
    "/{occasion_id}",
    operation_id="updateOccasion",
    summary="Update occasion",
    description="Replaces all fields of the occasion, including its links: a field left out "
    "is reset to its default or an empty list. The frontend sends the whole form."
    + _NOT_FOUND_NOTE
    + _TYPE_NOTE
    + _PEOPLE_NOTE
    + _BIRTHDAY_NOTE,
    responses=problem_responses(401, 404, 409),
)
async def update_occasion(
    occasion_id: uuid.UUID, body: OccasionIn, user: CurrentUser, session: SessionDep
) -> OccasionOut:
    """Replace all editable fields of an occasion of the current account."""
    occasion = await occasion_service.update_occasion(
        session, user.id, occasion_id, **body.model_dump()
    )
    return OccasionOut.model_validate(occasion)


@router.delete(
    "/{occasion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteOccasion",
    summary="Delete occasion",
    description="Deletes the occasion. Cannot be undone." + _NOT_FOUND_NOTE + _BIRTHDAY_NOTE,
    responses=problem_responses(401, 404, 409),
)
async def delete_occasion(occasion_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    """Delete an occasion of the current account."""
    await occasion_service.delete_occasion(session, user.id, occasion_id)
