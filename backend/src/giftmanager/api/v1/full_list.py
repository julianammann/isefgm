"""Complete list endpoint (F-15): the account's people, gift ideas and past gifts in one response."""

from fastapi import APIRouter

from giftmanager.core.auth import CurrentUser
from giftmanager.core.db import SessionDep
from giftmanager.schemas.common import problem_responses
from giftmanager.schemas.full_list import FullListGift, FullListOut
from giftmanager.schemas.gift import GiftOut
from giftmanager.schemas.gifting import GiftingOut
from giftmanager.schemas.link import LinkOut
from giftmanager.schemas.note import NoteOut
from giftmanager.schemas.person import PersonOut
from giftmanager.services import full_list as full_list_service

router = APIRouter(prefix="/full-list", tags=["full-list"])


@router.get(
    "",
    operation_id="getFullList",
    summary="Show complete list",
    description="Returns all people, all gift ideas with their links and notes, and all past "
    "gifts (giftings with status `given`) of the current account in one response. The "
    "frontend renders it as one HTML page. Not paginated on purpose: F-15 asks for the "
    "complete list; all rows are loaded in a fixed number of queries.",
    responses=problem_responses(401),
)
async def get_full_list(user: CurrentUser, session: SessionDep) -> FullListOut:
    """Return the current account's complete list."""
    full_list = await full_list_service.get_full_list(session, user.id)
    return FullListOut(
        people=[PersonOut.model_validate(person) for person in full_list.people],
        gifts=[
            FullListGift(
                **GiftOut.model_validate(item.gift).model_dump(),
                links=[LinkOut.model_validate(link) for link in item.links],
                notes=[NoteOut.model_validate(note) for note in item.notes],
            )
            for item in full_list.gifts
        ],
        given=[GiftingOut.model_validate(gifting) for gifting in full_list.given],
    )
