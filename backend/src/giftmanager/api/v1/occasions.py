"""Occasion type and occasion endpoints (F-03).

Create and update also link the occasion to the account's people (F-04).
"""

import datetime as dt
import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from giftmanager.core.auth import CurrentUser
from giftmanager.core.clock import ClockDep, local_today
from giftmanager.core.db import SessionDep
from giftmanager.models import RULE_TYPES, Occasion, OccasionType
from giftmanager.schemas.common import Page, PageParams, problem_responses
from giftmanager.schemas.occasion import OccasionIn, OccasionOut, OccasionTypeOut
from giftmanager.schemas.person import LinkedPerson
from giftmanager.services import occasion as occasion_service
from giftmanager.services.occasion import rule_date

types_router = APIRouter(prefix="/occasion-types", tags=["occasions"])
router = APIRouter(prefix="/occasions", tags=["occasions"])

_NOT_FOUND_NOTE = " An occasion of another account returns 404, like a missing one."
_TYPE_NOTE = (
    " `occasion_type_id` must be a system-wide type or one of the account; otherwise 404."
    " Geburtstag, Weihnachten and Ostern return 422: rule occasions exist once per account."
)
_RULE_NOTE = " A rule occasion (Geburtstag, Weihnachten, Ostern) cannot be changed or deleted; this returns 409."
_GIFTING_NOTE = " An occasion used by a gifting cannot be deleted; this returns 409."
_PEOPLE_NOTE = (
    " `person_ids` links the occasion to people of the account; an ID of another account"
    " returns 404, like a missing one, and nothing is saved."
)


def occasion_out(occasion: Occasion, today: dt.date) -> OccasionOut:
    """Map an occasion to its response body; a rule occasion shows its next date."""
    rule = RULE_TYPES.get(occasion.occasion_type_id) if occasion.occasion_type_id else None
    return OccasionOut(
        id=occasion.id,
        name=occasion.name,
        date=rule_date(rule, today) if rule else occasion.date,
        recurrence=occasion.recurrence,
        occasion_type_id=occasion.occasion_type_id,
        rule=rule,
        people=[LinkedPerson.model_validate(p) for p in occasion.people],
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
    description="Returns the system-wide types (Geburtstag, Ostern, Weihnachten, by name) followed by the "
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
    description="Returns the occasions of the current account, one page at a time: the rule "
    "occasions Geburtstag, Weihnachten and Ostern first, then the others sorted by month and "
    "day (the year is ignored). `total` counts all occasions of the account.",
    responses=problem_responses(401),
)
async def list_occasions(
    user: CurrentUser, session: SessionDep, clock: ClockDep, page: Annotated[PageParams, Query()]
) -> Page[OccasionOut]:
    """Return one page of the current account's occasions."""
    today = local_today(clock)
    occasions, total = await occasion_service.list_occasions(
        session, user.id, limit=page.limit, offset=page.offset
    )
    return Page[OccasionOut](
        items=[occasion_out(o, today) for o in occasions],
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
async def create_occasion(
    body: OccasionIn, user: CurrentUser, session: SessionDep, clock: ClockDep
) -> OccasionOut:
    """Create an occasion for the current account."""
    occasion = await occasion_service.create_occasion(session, user.id, **body.model_dump())
    return occasion_out(occasion, local_today(clock))


@router.get(
    "/{occasion_id}",
    operation_id="getOccasion",
    summary="Show occasion",
    description="Returns one occasion of the current account." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def get_occasion(
    occasion_id: uuid.UUID, user: CurrentUser, session: SessionDep, clock: ClockDep
) -> OccasionOut:
    """Return one occasion of the current account."""
    occasion = await occasion_service.get_occasion(session, user.id, occasion_id)
    return occasion_out(occasion, local_today(clock))


@router.put(
    "/{occasion_id}",
    operation_id="updateOccasion",
    summary="Update occasion",
    description="Replaces all fields of the occasion, including its links: a field left out "
    "is reset to its default or an empty list. The frontend sends the whole form."
    + _NOT_FOUND_NOTE
    + _TYPE_NOTE
    + _PEOPLE_NOTE
    + _RULE_NOTE,
    responses=problem_responses(401, 404, 409),
)
async def update_occasion(
    occasion_id: uuid.UUID,
    body: OccasionIn,
    user: CurrentUser,
    session: SessionDep,
    clock: ClockDep,
) -> OccasionOut:
    """Replace all editable fields of an occasion of the current account."""
    occasion = await occasion_service.update_occasion(
        session, user.id, occasion_id, **body.model_dump()
    )
    return occasion_out(occasion, local_today(clock))


@router.delete(
    "/{occasion_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteOccasion",
    summary="Delete occasion",
    description="Deletes the occasion. Cannot be undone."
    + _NOT_FOUND_NOTE
    + _RULE_NOTE
    + _GIFTING_NOTE,
    responses=problem_responses(401, 404, 409),
)
async def delete_occasion(occasion_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    """Delete an occasion of the current account."""
    await occasion_service.delete_occasion(session, user.id, occasion_id)
