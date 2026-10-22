"""Share link endpoints (F-14): manage links as the owner, open the read-only view by token."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status
from fastapi.responses import FileResponse

from giftmanager.api.v1.images import IMAGE_FILE_RESPONSE, image_response
from giftmanager.core.auth import CurrentUser
from giftmanager.core.clock import ClockDep
from giftmanager.core.db import SessionDep
from giftmanager.schemas.common import Page, PageParams, problem_responses
from giftmanager.schemas.share_link import (
    SharedGiftOut,
    SharedImageOut,
    SharedLinkOut,
    SharedListOut,
    SharedPersonOut,
    ShareLinkCreated,
    ShareLinkIn,
    ShareLinkOut,
)
from giftmanager.services import share_link as share_link_service

router = APIRouter(prefix="/share-links", tags=["share-links"])
shared_router = APIRouter(prefix="/shared", tags=["shared"])

_NOT_FOUND_NOTE = " A share link of another account returns 404, like a missing one."
_INPUT_NOTE = (
    " `person_ids` must name 1 to 100 people of the account; a person of another account"
    " returns 404, like a missing one, and nothing is saved. An `expires_at` that is set or"
    " changed must lie in the future (400 otherwise)."
)


@router.get(
    "",
    operation_id="listShareLinks",
    summary="List share links",
    description="Returns the share links of the current account, newest first, one page at a "
    "time. Tokens are not included; they are shown only once, on creation.",
    responses=problem_responses(401),
)
async def list_share_links(
    user: CurrentUser, session: SessionDep, page: Annotated[PageParams, Query()]
) -> Page[ShareLinkOut]:
    """Return one page of the current account's share links."""
    share_links, total = await share_link_service.list_share_links(
        session, user.id, limit=page.limit, offset=page.offset
    )
    return Page[ShareLinkOut](
        items=[ShareLinkOut.model_validate(s) for s in share_links],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    operation_id="createShareLink",
    summary="Create share link",
    description="Creates a read-only share link on chosen people of the current account. The "
    "response holds the token, the only time it is returned: the server keeps just its "
    "SHA-256 hash." + _INPUT_NOTE,
    responses=problem_responses(400, 401, 404),
)
async def create_share_link(
    body: ShareLinkIn, user: CurrentUser, session: SessionDep, clock: ClockDep
) -> ShareLinkCreated:
    """Create a share link for the current account and return its token once."""
    share_link, token = await share_link_service.create_share_link(
        session, user.id, **body.model_dump(), now=clock.now()
    )
    out = ShareLinkOut.model_validate(share_link)
    return ShareLinkCreated(**out.model_dump(), token=token)


@router.get(
    "/{share_link_id}",
    operation_id="getShareLink",
    summary="Show share link",
    description="Returns one share link of the current account, without its token."
    + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def get_share_link(
    share_link_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> ShareLinkOut:
    """Return one share link of the current account."""
    share_link = await share_link_service.get_share_link(session, user.id, share_link_id)
    return ShareLinkOut.model_validate(share_link)


@router.put(
    "/{share_link_id}",
    operation_id="updateShareLink",
    summary="Update share link",
    description="Replaces the people, expiry time and active flag of the share link. "
    "`active: false` deactivates it at once; the token stays the same."
    + _INPUT_NOTE
    + _NOT_FOUND_NOTE,
    responses=problem_responses(400, 401, 404),
)
async def update_share_link(
    share_link_id: uuid.UUID,
    body: ShareLinkIn,
    user: CurrentUser,
    session: SessionDep,
    clock: ClockDep,
) -> ShareLinkOut:
    """Replace the editable fields of a share link of the current account."""
    share_link = await share_link_service.update_share_link(
        session, user.id, share_link_id, **body.model_dump(), now=clock.now()
    )
    return ShareLinkOut.model_validate(share_link)


@router.delete(
    "/{share_link_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteShareLink",
    summary="Delete share link",
    description="Deletes the share link; it no longer opens. Cannot be undone." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def delete_share_link(
    share_link_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> None:
    """Delete a share link of the current account."""
    await share_link_service.delete_share_link(session, user.id, share_link_id)


@shared_router.get(
    "/{token}",
    operation_id="getSharedList",
    summary="Open shared list",
    description="Public, read-only view behind a share link, no login needed. Returns the "
    "chosen people with only their names and the gift ideas meant for them, with web links "
    "and images. "
    "An unknown, deactivated or expired token returns the same 404, so the response does not "
    "tell them apart. Other methods return 405.",
    responses=problem_responses(404),
)
async def get_shared_list(token: str, session: SessionDep, clock: ClockDep) -> SharedListOut:
    """Return the read-only view behind a share link."""
    shared = await share_link_service.get_shared_list(session, token, now=clock.now())
    return SharedListOut(
        owner_name=shared.owner_name,
        expires_at=shared.expires_at,
        people=[
            SharedPersonOut(
                name=p.person.name,
                gifts=[
                    SharedGiftOut(
                        title=g.gift.title,
                        description=g.gift.description,
                        price_from=g.gift.price_from,
                        price_to=g.gift.price_to,
                        currency=g.gift.currency,
                        category=g.gift.category,
                        links=[SharedLinkOut.model_validate(link) for link in g.links],
                        images=[SharedImageOut.model_validate(image) for image in g.images],
                    )
                    for g in p.gifts
                ],
            )
            for p in shared.people
        ],
    )


@shared_router.get(
    "/{token}/images/{image_id}",
    operation_id="getSharedImage",
    summary="Fetch shared image file",
    description="Public, no login needed: returns the WebP file of an image on one of the gift "
    "ideas the share link shows, marked `Cache-Control: private, no-store`. An unknown, "
    "deactivated or expired token, or an image the link does not show, returns the same 404 "
    "as the shared list.",
    response_class=FileResponse,
    responses=IMAGE_FILE_RESPONSE | problem_responses(404),
)
async def get_shared_image(
    token: str, image_id: uuid.UUID, session: SessionDep, clock: ClockDep
) -> FileResponse:
    """Return the file of an image the share link shows."""
    image = await share_link_service.get_shared_image(session, token, image_id, now=clock.now())
    return image_response(image)
