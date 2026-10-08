"""Gifting endpoints (F-06): list, create, show, update, delete.

Creating a gifting from an idea is one request (QZ-01); a past gift can be recorded directly
with status `given`.
"""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from giftmanager.core.auth import CurrentUser
from giftmanager.core.db import SessionDep
from giftmanager.schemas.common import Page, PageParams, problem_responses
from giftmanager.schemas.gifting import GiftingIn, GiftingOut
from giftmanager.services import gifting as gifting_service

router = APIRouter(prefix="/giftings", tags=["giftings"])

_NOT_FOUND_NOTE = " A gifting of another account returns 404, like a missing one."
_LINKS_NOTE = (
    " `gift_id`, `person_ids` and `occasion_id` must belong to the account; an ID of another"
    " account returns 404, like a missing one, and nothing is saved."
)
_GIVEN_NOTE = (
    " Status `given` needs at least one recipient, `occasion_id`, `occasion_date` and"
    " `given_on` (422 otherwise); `given_on` is not stored with any other status."
)


@router.get(
    "",
    operation_id="listGiftings",
    summary="List giftings",
    description="Returns the giftings of the current account, newest first, one page at a "
    "time. `total` counts all giftings of the account.",
    responses=problem_responses(401),
)
async def list_giftings(
    user: CurrentUser, session: SessionDep, page: Annotated[PageParams, Query()]
) -> Page[GiftingOut]:
    """Return one page of the current account's giftings."""
    giftings, total = await gifting_service.list_giftings(
        session, user.id, limit=page.limit, offset=page.offset
    )
    return Page[GiftingOut](
        items=[GiftingOut.model_validate(g) for g in giftings],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    operation_id="createGifting",
    summary="Create gifting",
    description="Turns a gift idea into a gifting in one step: only `gift_id` is required, "
    "the status defaults to `idea`. The idea is referenced, not copied, and stays in the "
    "idea list. A past gift is recorded directly with status `given`." + _GIVEN_NOTE + _LINKS_NOTE,
    responses=problem_responses(401, 404),
)
async def create_gifting(body: GiftingIn, user: CurrentUser, session: SessionDep) -> GiftingOut:
    """Create a gifting for the current account."""
    gifting = await gifting_service.create_gifting(session, user.id, **body.model_dump())
    return GiftingOut.model_validate(gifting)


@router.get(
    "/{gifting_id}",
    operation_id="getGifting",
    summary="Show gifting",
    description="Returns one gifting of the current account." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def get_gifting(gifting_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> GiftingOut:
    """Return one gifting of the current account."""
    gifting = await gifting_service.get_gifting(session, user.id, gifting_id)
    return GiftingOut.model_validate(gifting)


@router.put(
    "/{gifting_id}",
    operation_id="updateGifting",
    summary="Update gifting",
    description="Replaces all fields of the gifting, including its recipients: a field left "
    "out is reset to null, its default or an empty list. Any status may follow any other."
    + _GIVEN_NOTE
    + _LINKS_NOTE
    + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def update_gifting(
    gifting_id: uuid.UUID, body: GiftingIn, user: CurrentUser, session: SessionDep
) -> GiftingOut:
    """Replace all editable fields of a gifting of the current account."""
    gifting = await gifting_service.update_gifting(
        session, user.id, gifting_id, **body.model_dump()
    )
    return GiftingOut.model_validate(gifting)


@router.delete(
    "/{gifting_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteGifting",
    summary="Delete gifting",
    description="Deletes the gifting. The idea, the people and the occasion stay. Cannot be "
    "undone." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def delete_gifting(gifting_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    """Delete a gifting of the current account."""
    await gifting_service.delete_gifting(session, user.id, gifting_id)
