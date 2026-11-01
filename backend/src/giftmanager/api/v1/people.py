"""Person endpoints (F-02): list, create, show, update, delete; person view (F-09)."""

import uuid
from typing import Annotated

from fastapi import APIRouter, Query, status

from giftmanager.api.v1.occasions import occasion_out
from giftmanager.core.auth import CurrentUser
from giftmanager.core.clock import ClockDep, local_today
from giftmanager.core.db import SessionDep
from giftmanager.models import Gifting
from giftmanager.schemas.common import Page, PageParams, problem_responses
from giftmanager.schemas.gift import GiftOut
from giftmanager.schemas.gifting import GiftingOut
from giftmanager.schemas.occasion import OccasionOut
from giftmanager.schemas.person import PersonIn, PersonOut
from giftmanager.schemas.person_overview import OverviewGifting, PersonOverviewOut
from giftmanager.schemas.task import TaskOut
from giftmanager.services import person as person_service
from giftmanager.services import person_overview as person_overview_service

router = APIRouter(prefix="/people", tags=["people"])

_NOT_FOUND_NOTE = " A person of another account returns 404, like a missing one."


@router.get(
    "",
    operation_id="listPeople",
    summary="List people",
    description="Returns the people of the current account, sorted by name "
    "(case-insensitive), one page at a time. `total` counts all people of the account.",
    responses=problem_responses(401),
)
async def list_people(
    user: CurrentUser, session: SessionDep, page: Annotated[PageParams, Query()]
) -> Page[PersonOut]:
    """Return one page of the current account's people."""
    people, total = await person_service.list_people(
        session, user.id, limit=page.limit, offset=page.offset
    )
    return Page[PersonOut](
        items=[PersonOut.model_validate(p) for p in people],
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
    "empty optional fields are stored as null. Through `birthday` the person belongs to the "
    "account's rule occasion Geburtstag.",
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


@router.get(
    "/{person_id}/overview",
    operation_id="getPersonOverview",
    summary="Show person view",
    description="Returns what the person view shows (F-09): past gifts (`given`) and the "
    "giftings not given yet with their procurement state (`giftings`), both with occasion "
    "and tasks, the gift ideas meant for the person and not used for them yet (`ideas`) and "
    "the occasions that concern them (`occasions`). Every list is one page with the same `limit` and `offset` and its "
    "own `total`; all rows are loaded in a fixed number of queries." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def get_person_overview(
    person_id: uuid.UUID,
    user: CurrentUser,
    session: SessionDep,
    clock: ClockDep,
    page: Annotated[PageParams, Query()],
) -> PersonOverviewOut:
    """Return the person view of a person of the current account."""
    overview = await person_overview_service.get_person_overview(
        session, user.id, person_id, limit=page.limit, offset=page.offset
    )

    def with_tasks(giftings: tuple[list[Gifting], int]) -> Page[OverviewGifting]:
        items, total = giftings
        return Page[OverviewGifting](
            items=[
                OverviewGifting(
                    **GiftingOut.model_validate(gifting).model_dump(),
                    tasks=[TaskOut.model_validate(t) for t in overview.tasks.get(gifting.id, [])],
                )
                for gifting in items
            ],
            total=total,
            limit=page.limit,
            offset=page.offset,
        )

    ideas, ideas_total = overview.ideas
    occasions, occasions_total = overview.occasions
    today = local_today(clock)
    return PersonOverviewOut(
        given=with_tasks(overview.given),
        giftings=with_tasks(overview.giftings),
        ideas=Page[GiftOut](
            items=[GiftOut.model_validate(gift) for gift in ideas],
            total=ideas_total,
            limit=page.limit,
            offset=page.offset,
        ),
        occasions=Page[OccasionOut](
            items=[occasion_out(occasion, today) for occasion in occasions],
            total=occasions_total,
            limit=page.limit,
            offset=page.offset,
        ),
    )


@router.put(
    "/{person_id}",
    operation_id="updatePerson",
    summary="Update person",
    description="Replaces all fields of the person: a field left out is reset to null. "
    "The frontend sends the whole form. Through `birthday` the person belongs to the "
    "account's rule occasion Geburtstag." + _NOT_FOUND_NOTE,
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
