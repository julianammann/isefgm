"""Person endpoints (F-02): list, create, show, update, delete."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from giftmanager.core.auth import CurrentUser
from giftmanager.core.db import SessionDep
from giftmanager.schemas.common import Page, PageParams, problem_responses
from giftmanager.schemas.person import PersonIn, PersonOut
from giftmanager.services import person as person_service

router = APIRouter(prefix="/persons", tags=["persons"])

_NOT_FOUND_NOTE = " A person of another account returns 404, like a missing one."


@router.get(
    "",
    operation_id="listPersons",
    summary="List persons",
    description="Returns the persons of the current account, sorted by name "
    "(case-insensitive), one page at a time. `total` counts all persons of the account.",
    responses=problem_responses(401),
)
async def list_persons(
    user: CurrentUser, session: SessionDep, page: Annotated[PageParams, Query()]
) -> Page[PersonOut]:
    """Return one page of the current account's persons."""
    persons, total = await person_service.list_persons(
        session, user.id, limit=page.limit, offset=page.offset
    )
    return Page[PersonOut](
        items=[PersonOut.model_validate(p) for p in persons],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    operation_id="createPerson",
    summary="Create person",
    description="Creates a person for the current account. Only the name is required; "
    "empty optional fields are stored as null.",
    responses=problem_responses(401),
)
async def create_person(body: PersonIn, user: CurrentUser, session: SessionDep) -> PersonOut:
    """Create a person for the current account."""
    person = await person_service.create_person(session, user.id, **body.model_dump())
    return PersonOut.model_validate(person)


@router.get(
    "/{person_id}",
    operation_id="getPerson",
    summary="Show person",
    description="Returns one person of the current account." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def get_person(person_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> PersonOut:
    """Return one person of the current account."""
    person = await person_service.get_person(session, user.id, person_id)
    return PersonOut.model_validate(person)


@router.put(
    "/{person_id}",
    operation_id="updatePerson",
    summary="Update person",
    description="Replaces all fields of the person: a field left out is reset to null. "
    "The frontend sends the whole form." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def update_person(
    person_id: uuid.UUID, body: PersonIn, user: CurrentUser, session: SessionDep
) -> PersonOut:
    """Replace all editable fields of a person of the current account."""
    person = await person_service.update_person(session, user.id, person_id, **body.model_dump())
    return PersonOut.model_validate(person)


@router.delete(
    "/{person_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deletePerson",
    summary="Delete person",
    description="Deletes the person. Cannot be undone." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def delete_person(person_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    """Delete a person of the current account."""
    await person_service.delete_person(session, user.id, person_id)
