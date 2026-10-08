"""Gift idea endpoints (F-05): list, create, show, update, delete."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from giftmanager.core.auth import CurrentUser
from giftmanager.core.db import SessionDep
from giftmanager.schemas.common import Page, PageParams, problem_responses
from giftmanager.schemas.gift import GiftIn, GiftOut
from giftmanager.services import gift as gift_service

router = APIRouter(prefix="/gifts", tags=["gifts"])

_NOT_FOUND_NOTE = " A gift idea of another account returns 404, like a missing one."


@router.get(
    "",
    operation_id="listGifts",
    summary="List gift ideas",
    description="Returns the gift ideas of the current account, newest first, one page "
    "at a time. `total` counts all gift ideas of the account.",
    responses=problem_responses(401),
)
async def list_gifts(
    user: CurrentUser, session: SessionDep, page: Annotated[PageParams, Query()]
) -> Page[GiftOut]:
    """Return one page of the current account's gift ideas."""
    gifts, total = await gift_service.list_gifts(
        session, user.id, limit=page.limit, offset=page.offset
    )
    return Page[GiftOut](
        items=[GiftOut.model_validate(g) for g in gifts],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    operation_id="createGift",
    summary="Create gift idea",
    description="Creates a gift idea for the current account. Only the title is required, "
    "so an idea can be captured in one step: empty optional fields are stored as null and "
    "`category` defaults to `other`. `currency` is stored only with a price, EUR if none is "
    "given. The creation time is set by the server.",
    responses=problem_responses(401),
)
async def create_gift(body: GiftIn, user: CurrentUser, session: SessionDep) -> GiftOut:
    """Create a gift idea for the current account."""
    gift = await gift_service.create_gift(session, user.id, **body.model_dump())
    return GiftOut.model_validate(gift)


@router.get(
    "/{gift_id}",
    operation_id="getGift",
    summary="Show gift idea",
    description="Returns one gift idea of the current account." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def get_gift(gift_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> GiftOut:
    """Return one gift idea of the current account."""
    gift = await gift_service.get_gift(session, user.id, gift_id)
    return GiftOut.model_validate(gift)


@router.put(
    "/{gift_id}",
    operation_id="updateGift",
    summary="Update gift idea",
    description="Replaces all fields of the gift idea: a field left out is reset to null "
    "or its default. The frontend sends the whole form." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def update_gift(
    gift_id: uuid.UUID, body: GiftIn, user: CurrentUser, session: SessionDep
) -> GiftOut:
    """Replace all editable fields of a gift idea of the current account."""
    gift = await gift_service.update_gift(session, user.id, gift_id, **body.model_dump())
    return GiftOut.model_validate(gift)


@router.delete(
    "/{gift_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteGift",
    summary="Delete gift idea",
    description="Deletes the gift idea. Cannot be undone." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def delete_gift(gift_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    """Delete a gift idea of the current account."""
    await gift_service.delete_gift(session, user.id, gift_id)
