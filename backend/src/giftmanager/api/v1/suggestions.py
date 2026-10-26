"""Suggestion endpoints (F-16): make, list, show, accept and dismiss gift suggestions."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from giftmanager.core.auth import CurrentUser
from giftmanager.core.db import SessionDep
from giftmanager.schemas.common import Page, problem_responses
from giftmanager.schemas.gift import GiftOut
from giftmanager.schemas.suggestion import (
    SuggestionAccept,
    SuggestionListParams,
    SuggestionOut,
    SuggestionRequest,
)
from giftmanager.services import suggestion as suggestion_service

router = APIRouter(prefix="/suggestions", tags=["suggestions"])

_NOT_FOUND_NOTE = " A suggestion of another account returns 404, like a missing one."
_OPEN_NOTE = " Only an open suggestion can be accepted or dismissed; otherwise 409."


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    operation_id="createSuggestions",
    summary="Make suggestions",
    description="Replaces the open suggestions for a person of the current account with up to "
    f"{suggestion_service.MAX_SUGGESTIONS} new ones, most frequent first. Each is a category "
    "and price band shared by gift ideas of at least "
    f"{suggestion_service.MIN_ACCOUNTS} accounts; no title or text of another account is "
    "used (Q-04). Features the person already has as an idea or gifting, and features "
    "accepted or dismissed for them before, are left out. The list may be empty. A person of "
    "another account returns 404, like a missing one.",
    responses=problem_responses(401, 404),
)
async def create_suggestions(
    body: SuggestionRequest, user: CurrentUser, session: SessionDep
) -> list[SuggestionOut]:
    """Make new suggestions for a person of the current account."""
    suggestions = await suggestion_service.suggest_for_person(session, user.id, body.person_id)
    return [SuggestionOut.model_validate(s) for s in suggestions]


@router.get(
    "",
    operation_id="listSuggestions",
    summary="List suggestions",
    description="Returns the open suggestions of the current account, one page at a time, "
    "most frequent first. `person_id` narrows the list to one person; a person of another "
    "account gives an empty page.",
    responses=problem_responses(401),
)
async def list_suggestions(
    user: CurrentUser,
    session: SessionDep,
    page: Annotated[SuggestionListParams, Query()],
) -> Page[SuggestionOut]:
    """Return one page of the current account's open suggestions."""
    suggestions, total = await suggestion_service.list_suggestions(
        session, user.id, person_id=page.person_id, limit=page.limit, offset=page.offset
    )
    return Page[SuggestionOut](
        items=[SuggestionOut.model_validate(s) for s in suggestions],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.get(
    "/{suggestion_id}",
    operation_id="getSuggestion",
    summary="Show suggestion",
    description="Returns one suggestion of the current account in any status." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def get_suggestion(
    suggestion_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> SuggestionOut:
    """Return one suggestion of the current account."""
    suggestion = await suggestion_service.get_suggestion(session, user.id, suggestion_id)
    return SuggestionOut.model_validate(suggestion)


@router.post(
    "/{suggestion_id}/accept",
    status_code=status.HTTP_201_CREATED,
    operation_id="acceptSuggestion",
    summary="Accept suggestion",
    description="Creates a gift idea for the suggestion's person with the given title, the "
    "suggested category and the price range of the band in EUR, and marks the suggestion "
    "`accepted`. Returns the new gift idea." + _OPEN_NOTE + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404, 409),
)
async def accept_suggestion(
    suggestion_id: uuid.UUID, body: SuggestionAccept, user: CurrentUser, session: SessionDep
) -> GiftOut:
    """Turn a suggestion of the current account into a gift idea."""
    gift = await suggestion_service.accept_suggestion(
        session, user.id, suggestion_id, title=body.title
    )
    return GiftOut.model_validate(gift)


@router.post(
    "/{suggestion_id}/dismiss",
    operation_id="dismissSuggestion",
    summary="Dismiss suggestion",
    description="Marks the suggestion `dismissed`. Its category and price band are never "
    "suggested for the person again." + _OPEN_NOTE + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404, 409),
)
async def dismiss_suggestion(
    suggestion_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> SuggestionOut:
    """Dismiss a suggestion of the current account."""
    suggestion = await suggestion_service.dismiss_suggestion(session, user.id, suggestion_id)
    return SuggestionOut.model_validate(suggestion)
