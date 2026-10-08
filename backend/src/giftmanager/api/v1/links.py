"""Link endpoints (F-07): list, create, show, update, delete labelled links on gift ideas."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from giftmanager.core.auth import CurrentUser
from giftmanager.core.db import SessionDep
from giftmanager.schemas.common import Page, PageParams, problem_responses
from giftmanager.schemas.link import LinkIn, LinkOut
from giftmanager.services import link as link_service

router = APIRouter(prefix="/links", tags=["links"])

_NOT_FOUND_NOTE = " A link of another account returns 404, like a missing one."
_GIFT_NOTE = (
    " `gift_id` must be a gift idea of the account; an idea of another account returns 404,"
    " like a missing one, and nothing is saved. `url` must be an absolute http or https URL"
    " (422 otherwise)."
)


@router.get(
    "",
    operation_id="listLinks",
    summary="List links",
    description="Returns the links of the current account, oldest first, one page at a time. "
    "`gift_id` narrows the list to one idea; an idea of another account gives an empty page.",
    responses=problem_responses(401),
)
async def list_links(
    user: CurrentUser,
    session: SessionDep,
    page: Annotated[PageParams, Query()],
    gift_id: Annotated[
        uuid.UUID | None, Query(description="Only the links of this gift idea.")
    ] = None,
) -> Page[LinkOut]:
    """Return one page of the current account's links."""
    links, total = await link_service.list_links(
        session, user.id, gift_id=gift_id, limit=page.limit, offset=page.offset
    )
    return Page[LinkOut](
        items=[LinkOut.model_validate(link) for link in links],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    operation_id="createLink",
    summary="Create link",
    description="Adds a labelled link to a gift idea of the current account. The URL is "
    "stored as entered." + _GIFT_NOTE,
    responses=problem_responses(401, 404),
)
async def create_link(body: LinkIn, user: CurrentUser, session: SessionDep) -> LinkOut:
    """Add a link to a gift idea of the current account."""
    link = await link_service.create_link(session, user.id, **body.model_dump())
    return LinkOut.model_validate(link)


@router.get(
    "/{link_id}",
    operation_id="getLink",
    summary="Show link",
    description="Returns one link of the current account." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def get_link(link_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> LinkOut:
    """Return one link of the current account."""
    link = await link_service.get_link(session, user.id, link_id)
    return LinkOut.model_validate(link)


@router.put(
    "/{link_id}",
    operation_id="updateLink",
    summary="Update link",
    description="Replaces all fields of the link." + _GIFT_NOTE + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def update_link(
    link_id: uuid.UUID, body: LinkIn, user: CurrentUser, session: SessionDep
) -> LinkOut:
    """Replace all editable fields of a link of the current account."""
    link = await link_service.update_link(session, user.id, link_id, **body.model_dump())
    return LinkOut.model_validate(link)


@router.delete(
    "/{link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteLink",
    summary="Delete link",
    description="Deletes the link. Cannot be undone." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def delete_link(link_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    """Delete a link of the current account."""
    await link_service.delete_link(session, user.id, link_id)
