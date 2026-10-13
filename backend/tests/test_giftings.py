"""Giftings: concrete uses of a gift idea with their own status (F-06)."""

from datetime import date
from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import (
    Gift,
    Gifting,
    GiftingStatus,
    Occasion,
    Person,
    Recurrence,
    User,
    gifting_person,
)
from tests.accounts import log_in_new_user
from tests.ownership import ITEM_METHODS, assert_invisible_to_other_account

GIFTINGS = "/api/v1/giftings"
GIFTS = "/api/v1/gifts"
PEOPLE = "/api/v1/people"
OCCASIONS = "/api/v1/occasions"
ACCOUNT = "/api/v1/auth/account"
UNKNOWN_ID = "0192f6a0-0000-7000-8000-000000000000"


@pytest.fixture
async def anna(client: AsyncClient, session: AsyncSession) -> User:
    return await log_in_new_user(client, session, "anna@example.org")


async def create_gift(client: AsyncClient, title: str = "Raspberry Pi", **links: list[str]) -> str:
    return (await client.post(GIFTS, json={"title": title, **links})).json()["id"]


async def create_person(client: AsyncClient, name: str, birthday: str | None = None) -> str:
    return (await client.post(PEOPLE, json={"name": name, "birthday": birthday})).json()["id"]


async def create_occasion(client: AsyncClient) -> str:
    body = {"name": "Weihnachten", "date": "2025-12-24", "recurrence": "yearly"}
    return (await client.post(OCCASIONS, json=body)).json()["id"]


def given(gift: str, people: list[str], occasion: str) -> dict[str, Any]:
    """Body of a complete, given gifting: Christmas 2025, given on the day."""
    return {
        "gift_id": gift,
        "status": "given",
        "person_ids": people,
        "occasion_id": occasion,
        "occasion_date": "2025-12-24",
        "given_on": "2025-12-24",
    }


# --- Idea -> gifting, status and giving (F-06) --------------------------------


@pytest.mark.requirement("F-06")
async def test_idea_becomes_a_gifting_in_one_step(client: AsyncClient, anna: User) -> None:
    # QZ-01: one request turns an idea into a gifting; the idea is referenced, not copied.
    pi = await create_gift(client)
    lena = await create_person(client, "Lena")
    xmas = await create_occasion(client)
    idea_before = (await client.get(f"{GIFTS}/{pi}")).json()

    r = await client.post(
        GIFTINGS,
        json={
            "gift_id": pi,
            "status": "planned",
            "person_ids": [lena],
            "occasion_id": xmas,
            "occasion_date": "2026-12-24",
        },
    )
    assert r.status_code == 201
    created = r.json()
    assert created["gift"] == {"id": pi, "title": "Raspberry Pi"}
    assert created["status"] == "planned"
    assert created["people"] == [{"id": lena, "name": "Lena"}]
    assert created["occasion"] == {"id": xmas, "name": "Weihnachten"}
    assert created["occasion_date"] == "2026-12-24"
    assert created["given_on"] is None
    assert created["created_at"]

    assert (await client.get(f"{GIFTINGS}/{created['id']}")).json() == created
    # The idea stays in the idea list, unchanged and reusable.
    assert (await client.get(f"{GIFTS}/{pi}")).json() == idea_before


@pytest.mark.requirement("F-06")
async def test_gift_id_alone_creates_a_gifting_in_status_idea(
    client: AsyncClient, anna: User
) -> None:
    pi = await create_gift(client)

    r = await client.post(GIFTINGS, json={"gift_id": pi})
    assert r.status_code == 201
    body = r.json()
    assert body["status"] == "idea"
    assert body["people"] == []
    assert body["occasion"] is None
    assert body["occasion_date"] is None
    assert body["given_on"] is None


@pytest.mark.requirement("F-06")
@pytest.mark.parametrize("status", ["idea", "planned", "acquired"])
async def test_open_status_needs_no_recipient_or_date(
    client: AsyncClient, anna: User, status: str
) -> None:
    pi = await create_gift(client)

    r = await client.post(GIFTINGS, json={"gift_id": pi, "status": status})
    assert r.status_code == 201
    assert r.json()["status"] == status


@pytest.mark.requirement("F-06")
async def test_giving_records_recipients_occasion_and_date(client: AsyncClient, anna: User) -> None:
    pi = await create_gift(client)
    lena = await create_person(client, "Lena")
    xmas = await create_occasion(client)
    gifting = (await client.post(GIFTINGS, json={"gift_id": pi, "status": "acquired"})).json()

    r = await client.put(f"{GIFTINGS}/{gifting['id']}", json=given(pi, [lena], xmas))
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == gifting["id"]
    assert body["status"] == "given"
    assert body["people"] == [{"id": lena, "name": "Lena"}]
    assert body["occasion"] == {"id": xmas, "name": "Weihnachten"}
    assert body["occasion_date"] == "2025-12-24"
    assert body["given_on"] == "2025-12-24"
    assert body["created_at"] == gifting["created_at"]

    assert (await client.get(f"{GIFTINGS}/{gifting['id']}")).json() == body


@pytest.mark.requirement("F-06", "Q-08")
async def test_past_gift_is_recorded_directly(client: AsyncClient, anna: User) -> None:
    # No detour through idea, planned and acquired.
    pi = await create_gift(client)
    lena = await create_person(client, "Lena")
    xmas = await create_occasion(client)

    body = {**given(pi, [lena], xmas), "occasion_date": "2019-12-24", "given_on": "2019-12-23"}
    r = await client.post(GIFTINGS, json=body)
    assert r.status_code == 201
    assert r.json()["status"] == "given"
    # Plain calendar dates, without time or time zone.
    assert r.json()["occasion_date"] == "2019-12-24"
    assert r.json()["given_on"] == "2019-12-23"


@pytest.mark.requirement("F-06")
@pytest.mark.parametrize("missing", ["person_ids", "occasion_id", "occasion_date", "given_on"])
async def test_given_gifting_must_be_complete(
    client: AsyncClient, anna: User, missing: str
) -> None:
    pi = await create_gift(client)
    lena = await create_person(client, "Lena")
    xmas = await create_occasion(client)
    body = given(pi, [lena], xmas)
    del body[missing]

    r = await client.post(GIFTINGS, json=body)
    assert r.status_code == 422
    # The rule spans several fields, so the error points at the whole body.
    assert r.json()["errors"][0]["loc"] == ["body"]
    assert (await client.get(GIFTINGS)).json()["total"] == 0


@pytest.mark.requirement("F-06")
@pytest.mark.parametrize("status", ["idea", "planned", "acquired"])
async def test_given_on_is_only_stored_when_given(
    client: AsyncClient, anna: User, status: str
) -> None:
    # The form sends its date field whatever the status.
    pi = await create_gift(client)

    r = await client.post(
        GIFTINGS, json={"gift_id": pi, "status": status, "given_on": "2025-12-24"}
    )
    assert r.status_code == 201
    assert r.json()["given_on"] is None


@pytest.mark.requirement("F-06")
async def test_status_can_go_back_from_given(client: AsyncClient, anna: User) -> None:
    pi = await create_gift(client)
    lena = await create_person(client, "Lena")
    xmas = await create_occasion(client)
    gifting = (await client.post(GIFTINGS, json=given(pi, [lena], xmas))).json()

    r = await client.put(
        f"{GIFTINGS}/{gifting['id']}", json={**given(pi, [lena], xmas), "status": "acquired"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["status"] == "acquired"
    assert body["given_on"] is None
    assert body["people"] == [{"id": lena, "name": "Lena"}]
    assert body["occasion_date"] == "2025-12-24"


@pytest.mark.requirement("F-06")
async def test_update_replaces_all_fields(client: AsyncClient, anna: User) -> None:
    pi = await create_gift(client)
    book = await create_gift(client, "Buch")
    lena = await create_person(client, "Lena")
    xmas = await create_occasion(client)
    created = (
        await client.post(
            GIFTINGS,
            json={
                "gift_id": pi,
                "status": "planned",
                "person_ids": [lena],
                "occasion_id": xmas,
                "occasion_date": "2026-12-24",
            },
        )
    ).json()

    r = await client.put(f"{GIFTINGS}/{created['id']}", json={"gift_id": book})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == created["id"]
    assert body["gift"] == {"id": book, "title": "Buch"}
    assert body["status"] == "idea"
    assert body["people"] == []
    assert body["occasion"] is None
    assert body["occasion_date"] is None
    assert body["created_at"] == created["created_at"]


@pytest.mark.requirement("F-06", "Q-08")
@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({}, "gift_id"),
        ({"gift_id": "not-a-uuid"}, "gift_id"),
        ({"gift_id": UNKNOWN_ID, "status": "lost"}, "status"),
        ({"gift_id": UNKNOWN_ID, "status": None}, "status"),
        ({"gift_id": UNKNOWN_ID, "person_ids": None}, "person_ids"),
        ({"gift_id": UNKNOWN_ID, "person_ids": [UNKNOWN_ID] * 101}, "person_ids"),
        ({"gift_id": UNKNOWN_ID, "occasion_id": "xmas"}, "occasion_id"),
        ({"gift_id": UNKNOWN_ID, "occasion_date": "24.12.2026"}, "occasion_date"),
        ({"gift_id": UNKNOWN_ID, "given_on": "2026-12-24T18:00:00Z"}, "given_on"),
    ],
)
async def test_invalid_gifting_is_rejected(
    client: AsyncClient, anna: User, body: dict[str, object], field: str
) -> None:
    r = await client.post(GIFTINGS, json=body)
    assert r.status_code == 422
    assert r.json()["errors"][0]["loc"] == ["body", field]


# --- Joint and independent giftings (F-04, F-06) ------------------------------


@pytest.mark.requirement("F-04", "F-06")
async def test_joint_gift_for_several_people(client: AsyncClient, anna: User) -> None:
    pi = await create_gift(client)
    lena = await create_person(client, "Lena")
    anton = await create_person(client, "anton")

    r = await client.post(GIFTINGS, json={"gift_id": pi, "person_ids": [lena, anton]})
    assert r.status_code == 201
    # One gifting, one status for both; same order as the people list (by name).
    assert r.json()["people"] == [{"id": anton, "name": "anton"}, {"id": lena, "name": "Lena"}]


@pytest.mark.requirement("F-04", "F-06")
async def test_one_idea_for_independent_giftings(client: AsyncClient, anna: User) -> None:
    pi = await create_gift(client)
    lena = await create_person(client, "Lena")
    anton = await create_person(client, "Anton")
    for_lena = (await client.post(GIFTINGS, json={"gift_id": pi, "person_ids": [lena]})).json()
    for_anton = (await client.post(GIFTINGS, json={"gift_id": pi, "person_ids": [anton]})).json()

    await client.put(
        f"{GIFTINGS}/{for_lena['id']}",
        json={"gift_id": pi, "status": "acquired", "person_ids": [lena]},
    )

    # Each gifting keeps its own status.
    assert (await client.get(f"{GIFTINGS}/{for_lena['id']}")).json()["status"] == "acquired"
    assert (await client.get(f"{GIFTINGS}/{for_anton['id']}")).json()["status"] == "idea"
    assert (await client.get(GIFTINGS)).json()["total"] == 2


@pytest.mark.requirement("F-06")
async def test_recipients_need_not_be_linked_to_the_idea(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, "Lena")
    anton = await create_person(client, "Anton")
    pi = await create_gift(client, person_ids=[lena])

    r = await client.post(GIFTINGS, json={"gift_id": pi, "person_ids": [anton]})
    assert r.status_code == 201
    assert r.json()["people"] == [{"id": anton, "name": "Anton"}]
    # The idea's possible recipients stay as they were.
    assert (await client.get(f"{GIFTS}/{pi}")).json()["people"] == [{"id": lena, "name": "Lena"}]


@pytest.mark.requirement("F-06")
async def test_gifting_shows_the_current_idea(client: AsyncClient, anna: User) -> None:
    pi = await create_gift(client)
    gifting = (await client.post(GIFTINGS, json={"gift_id": pi})).json()

    await client.put(f"{GIFTS}/{pi}", json={"title": "Raspberry Pi 5"})

    shown = (await client.get(f"{GIFTINGS}/{gifting['id']}")).json()
    assert shown["gift"] == {"id": pi, "title": "Raspberry Pi 5"}


# --- Show, list, delete --------------------------------------------------------


@pytest.mark.requirement("F-06")
async def test_delete_gifting(client: AsyncClient, anna: User) -> None:
    pi = await create_gift(client)
    gifting = (await client.post(GIFTINGS, json={"gift_id": pi})).json()

    assert (await client.delete(f"{GIFTINGS}/{gifting['id']}")).status_code == 204
    assert (await client.get(f"{GIFTINGS}/{gifting['id']}")).status_code == 404
    assert (await client.delete(f"{GIFTINGS}/{gifting['id']}")).status_code == 404
    # The idea stays.
    assert (await client.get(f"{GIFTS}/{pi}")).status_code == 200


@pytest.mark.requirement("F-06", "Q-05")
async def test_list_is_newest_first_and_paginated(client: AsyncClient, anna: User) -> None:
    for title in ["erste", "zweite", "dritte"]:
        await client.post(GIFTINGS, json={"gift_id": await create_gift(client, title)})

    first = await client.get(GIFTINGS, params={"limit": 2, "offset": 0})
    assert first.status_code == 200
    assert [g["gift"]["title"] for g in first.json()["items"]] == ["dritte", "zweite"]
    assert first.json()["total"] == 3
    assert first.json()["limit"] == 2
    assert first.json()["offset"] == 0

    second = await client.get(GIFTINGS, params={"limit": 2, "offset": 2})
    assert [g["gift"]["title"] for g in second.json()["items"]] == ["erste"]
    assert second.json()["total"] == 3


@pytest.mark.requirement("F-06", "Q-05")
async def test_list_rejects_oversized_page(client: AsyncClient, anna: User) -> None:
    r = await client.get(GIFTINGS, params={"limit": 201})
    assert r.status_code == 422


@pytest.mark.requirement("F-06")
async def test_unknown_or_malformed_id(client: AsyncClient, anna: User) -> None:
    assert (await client.get(f"{GIFTINGS}/{UNKNOWN_ID}")).status_code == 404
    assert (await client.get(f"{GIFTINGS}/not-a-uuid")).status_code == 422


@pytest.mark.requirement("F-06", "Q-01")
async def test_giftings_require_login(client: AsyncClient) -> None:
    assert (await client.get(GIFTINGS)).status_code == 401
    assert (await client.post(GIFTINGS, json={"gift_id": UNKNOWN_ID})).status_code == 401


# --- Tenant separation (Q-01) --------------------------------------------------


@pytest.mark.requirement("F-06", "Q-01")
@pytest.mark.parametrize("method", ITEM_METHODS)
async def test_giftings_of_another_account_are_invisible(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    pi = await create_gift(client)
    gifting = (await client.post(GIFTINGS, json={"gift_id": pi})).json()

    await assert_invisible_to_other_account(
        client,
        session,
        method=method,
        collection=GIFTINGS,
        item_id=gifting["id"],
        replacement={"gift_id": pi},
    )


@pytest.mark.requirement("F-06", "Q-01")
@pytest.mark.parametrize("method", ["POST", "PUT"])
@pytest.mark.parametrize("field", ["gift_id", "person_ids", "occasion_id"])
async def test_records_of_another_account_cannot_be_used(
    client: AsyncClient, session: AsyncSession, anna: User, method: str, field: str
) -> None:
    bob = User(email="bob@example.org", password_hash="not-a-real-hash", display_name="Bob")
    session.add(bob)
    await session.flush()
    bobs_gift = Gift(owner_id=bob.id, title="Bobs Idee")
    bobs_sister = Person(owner_id=bob.id, name="Bobs Schwester")
    bobs_birthday = Occasion(
        owner_id=bob.id, name="Bobs Geburtstag", date=date(1990, 5, 1), recurrence=Recurrence.YEARLY
    )
    session.add_all([bobs_gift, bobs_sister, bobs_birthday])
    await session.flush()
    pi = await create_gift(client)
    lena = await create_person(client, "Lena")
    gifting = (await client.post(GIFTINGS, json={"gift_id": pi})).json()

    # An own person next to the foreign one does not get linked either.
    foreign: dict[str, object] = {
        "gift_id": str(bobs_gift.id),
        "person_ids": [lena, str(bobs_sister.id)],
        "occasion_id": str(bobs_birthday.id),
    }
    body = {"gift_id": pi, "status": "planned", field: foreign[field]}
    url = GIFTINGS if method == "POST" else f"{GIFTINGS}/{gifting['id']}"
    r = await client.request(method, url, json=body)
    assert r.status_code == 404
    assert r.json()["title"] == "Not Found"

    assert (await client.get(GIFTINGS)).json()["items"] == [gifting]


@pytest.mark.requirement("F-06")
@pytest.mark.parametrize(
    ("field", "value"),
    [("gift_id", UNKNOWN_ID), ("person_ids", [UNKNOWN_ID]), ("occasion_id", UNKNOWN_ID)],
)
async def test_using_an_unknown_id_returns_404(
    client: AsyncClient, anna: User, field: str, value: object
) -> None:
    pi = await create_gift(client)

    r = await client.post(GIFTINGS, json={"gift_id": pi, field: value})
    assert r.status_code == 404
    assert (await client.get(GIFTINGS)).json()["total"] == 0


# --- Deleting what a gifting refers to (F-06) ----------------------------------


@pytest.mark.requirement("F-06")
async def test_idea_with_giftings_cannot_be_deleted(client: AsyncClient, anna: User) -> None:
    pi = await create_gift(client)
    gifting = (await client.post(GIFTINGS, json={"gift_id": pi})).json()

    r = await client.delete(f"{GIFTS}/{pi}")
    assert r.status_code == 409
    assert r.json()["title"] == "Conflict"
    assert (await client.get(f"{GIFTS}/{pi}")).status_code == 200

    # Once its giftings are gone, the idea can be deleted.
    assert (await client.delete(f"{GIFTINGS}/{gifting['id']}")).status_code == 204
    assert (await client.delete(f"{GIFTS}/{pi}")).status_code == 204


@pytest.mark.requirement("F-03", "F-06")
async def test_occasion_with_giftings_cannot_be_deleted(client: AsyncClient, anna: User) -> None:
    pi = await create_gift(client)
    xmas = await create_occasion(client)
    gifting = (await client.post(GIFTINGS, json={"gift_id": pi, "occasion_id": xmas})).json()

    r = await client.delete(f"{OCCASIONS}/{xmas}")
    assert r.status_code == 409
    assert r.json()["title"] == "Conflict"

    assert (await client.get(f"{OCCASIONS}/{xmas}")).status_code == 200
    shown = (await client.get(f"{GIFTINGS}/{gifting['id']}")).json()
    assert shown["occasion"] == {"id": xmas, "name": "Weihnachten"}


@pytest.mark.requirement("F-03", "F-06")
@pytest.mark.parametrize(("method", "body"), [("DELETE", None), ("PUT", {"name": "Lena"})])
async def test_birthday_with_giftings_cannot_be_removed(
    client: AsyncClient, anna: User, method: str, body: dict[str, object] | None
) -> None:
    # Deleting the person or clearing the birthday would delete the birthday occasion.
    lena = await create_person(client, "Lena", "1990-05-01")
    [birthday] = (await client.get(OCCASIONS)).json()["items"]
    pi = await create_gift(client)
    await client.post(
        GIFTINGS, json={"gift_id": pi, "person_ids": [lena], "occasion_id": birthday["id"]}
    )

    r = await client.request(method, f"{PEOPLE}/{lena}", json=body)
    assert r.status_code == 409
    assert r.json()["title"] == "Conflict"

    assert (await client.get(f"{PEOPLE}/{lena}")).json()["birthday"] == "1990-05-01"
    assert (await client.get(f"{OCCASIONS}/{birthday['id']}")).status_code == 200


@pytest.mark.requirement("F-06")
async def test_deleting_a_recipient_removes_them_from_the_gifting(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    pi = await create_gift(client)
    lena = await create_person(client, "Lena")
    anton = await create_person(client, "Anton")
    gifting = (
        await client.post(GIFTINGS, json={"gift_id": pi, "person_ids": [lena, anton]})
    ).json()

    assert (await client.delete(f"{PEOPLE}/{lena}")).status_code == 204
    # Each request has its own session in production; drop what this one still holds.
    session.expire_all()

    shown = (await client.get(f"{GIFTINGS}/{gifting['id']}")).json()
    assert shown["people"] == [{"id": anton, "name": "Anton"}]


# --- Database rules and account deletion ---------------------------------------


@pytest.mark.requirement("F-06")
@pytest.mark.parametrize("missing", ["occasion_id", "occasion_date", "given_on"])
async def test_database_requires_a_complete_given_gifting(
    session: AsyncSession, anna: User, missing: str
) -> None:
    # Bypasses the API: ck_gifting_given_complete holds even if validation is skipped.
    gift = Gift(owner_id=anna.id, title="Pi")
    xmas = Occasion(
        owner_id=anna.id, name="Weihnachten", date=date(2025, 12, 24), recurrence=Recurrence.YEARLY
    )
    session.add_all([gift, xmas])
    await session.flush()
    fields: dict[str, Any] = {
        "occasion_id": xmas.id,
        "occasion_date": date(2025, 12, 24),
        "given_on": date(2025, 12, 24),
    }
    fields[missing] = None

    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            session.add(Gifting(gift_id=gift.id, status=GiftingStatus.GIVEN, **fields))
            await session.flush()


@pytest.mark.requirement("F-06", "F-17")
async def test_deleting_the_account_deletes_its_giftings(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    # Also guards the foreign keys: RESTRICT on gift_id or occasion_id would block this.
    pi = await create_gift(client)
    lena = await create_person(client, "Lena")
    xmas = await create_occasion(client)
    assert (await client.post(GIFTINGS, json=given(pi, [lena], xmas))).status_code == 201

    assert (await client.delete(ACCOUNT)).status_code == 204
    assert await session.scalar(select(func.count()).select_from(Gifting)) == 0
    assert await session.scalar(select(func.count()).select_from(gifting_person)) == 0
