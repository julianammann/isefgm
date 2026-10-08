"""Note endpoints (F-07): list, create, show, update, delete labelled notes on gift ideas."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from giftmanager.core.auth import CurrentUser
from giftmanager.core.db import SessionDep
from giftmanager.schemas.common import Page, PageParams, problem_responses
from giftmanager.schemas.note import NoteIn, NoteOut
from giftmanager.services import note as note_service

router = APIRouter(prefix="/notes", tags=["notes"])

_NOT_FOUND_NOTE = " A note of another account returns 404, like a missing one."
_GIFT_NOTE = (
    " `gift_id` must be a gift idea of the account; an idea of another account returns 404,"
    " like a missing one, and nothing is saved."
)


@router.get(
    "",
    operation_id="listNotes",
    summary="List notes",
    description="Returns the notes of the current account, oldest first, one page at a time. "
    "`gift_id` narrows the list to one idea; an idea of another account gives an empty page.",
    responses=problem_responses(401),
)
async def list_notes(
    user: CurrentUser,
    session: SessionDep,
    page: Annotated[PageParams, Query()],
    gift_id: Annotated[
        uuid.UUID | None, Query(description="Only the notes of this gift idea.")
    ] = None,
) -> Page[NoteOut]:
    """Return one page of the current account's notes."""
    notes, total = await note_service.list_notes(
        session, user.id, gift_id=gift_id, limit=page.limit, offset=page.offset
    )
    return Page[NoteOut](
        items=[NoteOut.model_validate(n) for n in notes],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    operation_id="createNote",
    summary="Create note",
    description="Adds a labelled note to a gift idea of the current account." + _GIFT_NOTE,
    responses=problem_responses(401, 404),
)
async def create_note(body: NoteIn, user: CurrentUser, session: SessionDep) -> NoteOut:
    """Add a note to a gift idea of the current account."""
    note = await note_service.create_note(session, user.id, **body.model_dump())
    return NoteOut.model_validate(note)


@router.get(
    "/{note_id}",
    operation_id="getNote",
    summary="Show note",
    description="Returns one note of the current account." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def get_note(note_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> NoteOut:
    """Return one note of the current account."""
    note = await note_service.get_note(session, user.id, note_id)
    return NoteOut.model_validate(note)


@router.put(
    "/{note_id}",
    operation_id="updateNote",
    summary="Update note",
    description="Replaces all fields of the note." + _GIFT_NOTE + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def update_note(
    note_id: uuid.UUID, body: NoteIn, user: CurrentUser, session: SessionDep
) -> NoteOut:
    """Replace all editable fields of a note of the current account."""
    note = await note_service.update_note(session, user.id, note_id, **body.model_dump())
    return NoteOut.model_validate(note)


@router.delete(
    "/{note_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteNote",
    summary="Delete note",
    description="Deletes the note. Cannot be undone." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def delete_note(note_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    """Delete a note of the current account."""
    await note_service.delete_note(session, user.id, note_id)
