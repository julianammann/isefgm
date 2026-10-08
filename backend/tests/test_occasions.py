import datetime as dt

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import (
    BIRTHDAY_TYPE_ID,
    CHRISTMAS_TYPE_ID,
    Occasion,
    OccasionType,
    Person,
    Recurrence,
    User,
    person_occasion,
)
from giftmanager.services.occasion import next_occurrence
from tests.accounts import log_in_new_user
from tests.ownership import ITEM_METHODS, assert_invisible_to_other_account

TYPES = "/api/v1/occasion-types"
OCCASIONS = "/api/v1/occasions"
PEOPLE = "/api/v1/people"
ACCOUNT = "/api/v1/auth/account"
UNKNOWN_ID = "0192f6a0-0000-7000-8000-000000000000"

WEDDING = {"name": "Hochzeitstag", "date": "2019-06-21", "recurrence": "yearly"}


@pytest.fixture
async def anna(client: AsyncClient, session: AsyncSession) -> User:
    return await log_in_new_user(client, session, "anna@example.org")


async def create_person(client: AsyncClient, name: str) -> str:
    return (await client.post(PEOPLE, json={"name": name})).json()["id"]


@pytest.mark.requirement("F-03")
async def test_fixed_types_are_available_to_every_account(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    for next_user in ["bob@example.org", "carla@example.org"]:
        r = await client.get(TYPES)
        assert r.status_code == 200
        body = r.json()
        assert body["total"] == 2
        assert body["items"] == [
            {
                "id": str(BIRTHDAY_TYPE_ID),
                "name": "Geburtstag",
                "default_recurrence": "yearly",
                "system": True,
            },
            {
                "id": str(CHRISTMAS_TYPE_ID),
                "name": "Weihnachten",
                "default_recurrence": "yearly",
                "system": True,
            },
        ]
        await log_in_new_user(client, session, next_user)


@pytest.mark.requirement("F-03")
async def test_fixed_types_cannot_be_changed_or_deleted(client: AsyncClient, anna: User) -> None:
    url = f"{TYPES}/{BIRTHDAY_TYPE_ID}"
    assert (await client.put(url, json={"name": "Party"})).status_code == 405
    assert (await client.patch(url, json={"name": "Party"})).status_code == 405
    assert (await client.delete(url)).status_code == 405
    assert (await client.post(TYPES, json={"name": "Party"})).status_code == 405

    r = await client.get(url)
    assert r.status_code == 200
    assert r.json()["name"] == "Geburtstag"


@pytest.mark.requirement("F-03", "Q-08")
async def test_create_and_show_own_yearly_occasion(client: AsyncClient, anna: User) -> None:
    r = await client.post(OCCASIONS, json=WEDDING)
    assert r.status_code == 201
    created = r.json()
    assert created["name"] == "Hochzeitstag"
    assert created["date"] == "2019-06-21"
    assert created["recurrence"] == "yearly"
    assert created["occasion_type_id"] is None

    shown = await client.get(f"{OCCASIONS}/{created['id']}")
    assert shown.status_code == 200
    assert shown.json() == created


@pytest.mark.requirement("F-03")
async def test_one_off_is_the_default_and_fixed_types_can_be_used(
    client: AsyncClient, anna: User
) -> None:
    r = await client.post(
        OCCASIONS,
        json={
            "name": "Weihnachten 2026",
            "date": "2026-12-24",
            "occasion_type_id": str(CHRISTMAS_TYPE_ID),
        },
    )
    assert r.status_code == 201
    assert r.json()["recurrence"] == "none"
    assert r.json()["occasion_type_id"] == str(CHRISTMAS_TYPE_ID)


@pytest.mark.requirement("F-03", "Q-08")
@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"date": "2019-06-21"}, "name"),
        ({"name": "  ", "date": "2019-06-21"}, "name"),
        ({"name": "x" * 101, "date": "2019-06-21"}, "name"),
        ({"name": "Jahrestag"}, "date"),
        ({"name": "Jahrestag", "date": "21.06.2019"}, "date"),
        ({"name": "Jahrestag", "date": "2019-06-21T10:00:00Z"}, "date"),
        ({"name": "Jahrestag", "date": "2019-02-30"}, "date"),
        ({"name": "Jahrestag", "date": "2019-06-21", "recurrence": "monthly"}, "recurrence"),
        ({"name": "Jahrestag", "date": "2019-06-21", "occasion_type_id": "x"}, "occasion_type_id"),
        ({"name": "Jahrestag", "date": "2019-06-21", "person_ids": None}, "person_ids"),
        ({"name": "Jahrestag", "date": "2019-06-21", "person_ids": UNKNOWN_ID}, "person_ids"),
        (
            {"name": "Jahrestag", "date": "2019-06-21", "person_ids": [UNKNOWN_ID] * 101},
            "person_ids",
        ),
    ],
)
async def test_invalid_occasion_is_rejected(
    client: AsyncClient, anna: User, body: dict[str, object], field: str
) -> None:
    r = await client.post(OCCASIONS, json=body)
    assert r.status_code == 422
    assert r.json()["errors"][0]["loc"] == ["body", field]


@pytest.mark.requirement("F-03")
async def test_unknown_type_is_not_found(client: AsyncClient, anna: User) -> None:
    r = await client.post(
        OCCASIONS, json={**WEDDING, "occasion_type_id": "0192f6a0-0000-7000-8000-000000000000"}
    )
    assert r.status_code == 404
    assert (await client.get(OCCASIONS)).json()["total"] == 0


@pytest.mark.requirement("F-03")
async def test_update_replaces_all_fields(client: AsyncClient, anna: User) -> None:
    created = (await client.post(OCCASIONS, json=WEDDING)).json()

    r = await client.put(
        f"{OCCASIONS}/{created['id']}", json={"name": "Jahrestag", "date": "2020-07-01"}
    )
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == created["id"]
    assert body["name"] == "Jahrestag"
    assert body["date"] == "2020-07-01"
    assert body["recurrence"] == "none"


@pytest.mark.requirement("F-03")
async def test_delete_occasion(client: AsyncClient, anna: User) -> None:
    created = (await client.post(OCCASIONS, json=WEDDING)).json()

    assert (await client.delete(f"{OCCASIONS}/{created['id']}")).status_code == 204
    assert (await client.get(f"{OCCASIONS}/{created['id']}")).status_code == 404
    assert (await client.delete(f"{OCCASIONS}/{created['id']}")).status_code == 404


@pytest.mark.requirement("F-03", "Q-05")
async def test_list_is_sorted_by_date_and_paginated(client: AsyncClient, anna: User) -> None:
    for name, date in [("C", "2021-03-01"), ("A", "2019-01-01"), ("B", "2020-02-01")]:
        await client.post(OCCASIONS, json={"name": name, "date": date})

    first = await client.get(OCCASIONS, params={"limit": 2, "offset": 0})
    assert first.status_code == 200
    assert [o["name"] for o in first.json()["items"]] == ["A", "B"]
    assert first.json()["total"] == 3

    second = await client.get(OCCASIONS, params={"limit": 2, "offset": 2})
    assert [o["name"] for o in second.json()["items"]] == ["C"]


@pytest.mark.requirement("F-03", "Q-01")
@pytest.mark.parametrize("method", ITEM_METHODS)
async def test_occasions_of_another_account_are_invisible(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    wedding = (await client.post(OCCASIONS, json=WEDDING)).json()

    await assert_invisible_to_other_account(
        client,
        session,
        method=method,
        collection=OCCASIONS,
        item_id=wedding["id"],
        replacement={"name": "Hacked", "date": "2020-01-01"},
    )


@pytest.mark.requirement("F-03", "Q-01")
async def test_type_of_another_account_cannot_be_used(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    bob = User(email="bob@example.org", password_hash="not-a-real-hash", display_name="Bob")
    session.add(bob)
    await session.flush()
    bobs_type = OccasionType(owner_id=bob.id, name="Bobs Typ", default_recurrence=Recurrence.NONE)
    session.add(bobs_type)
    await session.flush()

    assert (await client.get(f"{TYPES}/{bobs_type.id}")).status_code == 404
    assert (await client.get(TYPES)).json()["total"] == 2

    r = await client.post(OCCASIONS, json={**WEDDING, "occasion_type_id": str(bobs_type.id)})
    assert r.status_code == 404

    created = (await client.post(OCCASIONS, json=WEDDING)).json()
    r = await client.put(
        f"{OCCASIONS}/{created['id']}", json={**WEDDING, "occasion_type_id": str(bobs_type.id)}
    )
    assert r.status_code == 404


@pytest.mark.requirement("F-03", "Q-01")
async def test_occasions_require_login(client: AsyncClient) -> None:
    assert (await client.get(TYPES)).status_code == 401
    assert (await client.get(OCCASIONS)).status_code == 401
    assert (await client.post(OCCASIONS, json=WEDDING)).status_code == 401


@pytest.mark.requirement("F-03", "F-17")
async def test_deleting_the_account_deletes_its_occasions(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    await client.post(OCCASIONS, json=WEDDING)

    assert (await client.delete(ACCOUNT)).status_code == 204
    count = select(func.count()).select_from(Occasion).where(Occasion.owner_id == anna.id)
    assert await session.scalar(count) == 0
    assert await session.get(OccasionType, BIRTHDAY_TYPE_ID) is not None


@pytest.mark.requirement("F-03", "Q-08")
@pytest.mark.parametrize(
    ("start", "recurrence", "today", "expected"),
    [
        ("2026-12-24", Recurrence.NONE, "2026-10-04", "2026-12-24"),
        ("2026-10-04", Recurrence.NONE, "2026-10-04", "2026-10-04"),
        ("2026-10-03", Recurrence.NONE, "2026-10-04", None),
        ("2019-06-21", Recurrence.YEARLY, "2026-03-01", "2026-06-21"),
        ("2019-06-21", Recurrence.YEARLY, "2026-06-21", "2026-06-21"),
        ("2019-06-21", Recurrence.YEARLY, "2026-06-22", "2027-06-21"),
        ("2020-01-05", Recurrence.YEARLY, "2026-12-30", "2027-01-05"),
        ("2019-12-31", Recurrence.YEARLY, "2026-12-31", "2026-12-31"),
        ("2019-12-31", Recurrence.YEARLY, "2027-01-01", "2027-12-31"),
        ("2030-05-01", Recurrence.YEARLY, "2026-10-04", "2030-05-01"),
        ("2020-02-29", Recurrence.YEARLY, "2026-01-10", "2026-02-28"),
        ("2020-02-29", Recurrence.YEARLY, "2027-03-01", "2028-02-29"),
        ("2020-02-29", Recurrence.YEARLY, "2028-02-29", "2028-02-29"),
        ("2020-02-29", Recurrence.YEARLY, "2028-03-01", "2029-02-28"),
    ],
)
def test_next_occurrence(
    start: str, recurrence: Recurrence, today: str, expected: str | None
) -> None:
    result = next_occurrence(dt.date.fromisoformat(start), recurrence, dt.date.fromisoformat(today))
    assert result == (dt.date.fromisoformat(expected) if expected else None)


# --- Links to people (F-04) ---------------------------------------------------


@pytest.mark.requirement("F-04")
async def test_occasion_without_people(client: AsyncClient, anna: User) -> None:
    r = await client.post(OCCASIONS, json=WEDDING)
    assert r.status_code == 201
    assert r.json()["people"] == []


@pytest.mark.requirement("F-04")
async def test_occasion_links_people(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, "Lena")
    anton = await create_person(client, "anton")

    r = await client.post(OCCASIONS, json={**WEDDING, "person_ids": [lena, anton]})
    assert r.status_code == 201
    created = r.json()
    # Same order as the people list: by name, ignoring case.
    assert created["people"] == [{"id": anton, "name": "anton"}, {"id": lena, "name": "Lena"}]

    assert (await client.get(f"{OCCASIONS}/{created['id']}")).json() == created
    assert (await client.get(OCCASIONS)).json()["items"] == [created]


@pytest.mark.requirement("F-04")
async def test_update_replaces_people(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, "Lena")
    anton = await create_person(client, "Anton")
    created = (await client.post(OCCASIONS, json={**WEDDING, "person_ids": [lena]})).json()
    url = f"{OCCASIONS}/{created['id']}"

    r = await client.put(url, json={**WEDDING, "person_ids": [anton]})
    assert r.status_code == 200
    assert r.json()["people"] == [{"id": anton, "name": "Anton"}]

    # person_ids left out: a PUT replaces everything, so the people are unlinked.
    r = await client.put(url, json=WEDDING)
    assert r.status_code == 200
    assert r.json()["people"] == []
    assert (await client.get(url)).json() == r.json()

    # Unlinking keeps the people.
    assert (await client.get(f"{PEOPLE}/{lena}")).status_code == 200
    assert (await client.get(f"{PEOPLE}/{anton}")).status_code == 200


@pytest.mark.requirement("F-04")
async def test_people_and_occasions_are_many_to_many(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, "Lena")
    anton = await create_person(client, "Anton")

    # One occasion for several people ...
    wedding = await client.post(OCCASIONS, json={**WEDDING, "person_ids": [lena, anton]})
    # ... and one person with several occasions.
    party = await client.post(
        OCCASIONS, json={"name": "Abifeier", "date": "2026-07-03", "person_ids": [lena]}
    )

    assert [p["name"] for p in wedding.json()["people"]] == ["Anton", "Lena"]
    assert [p["name"] for p in party.json()["people"]] == ["Lena"]


@pytest.mark.requirement("F-04")
async def test_repeated_person_id_is_linked_once(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, "Lena")

    r = await client.post(OCCASIONS, json={**WEDDING, "person_ids": [lena, lena]})
    assert r.status_code == 201
    assert r.json()["people"] == [{"id": lena, "name": "Lena"}]


@pytest.mark.requirement("F-04")
async def test_linking_an_unknown_person_returns_404(client: AsyncClient, anna: User) -> None:
    r = await client.post(OCCASIONS, json={**WEDDING, "person_ids": [UNKNOWN_ID]})
    assert r.status_code == 404
    assert (await client.get(OCCASIONS)).json()["total"] == 0


@pytest.mark.requirement("F-04", "Q-01")
@pytest.mark.parametrize("method", ["POST", "PUT"])
async def test_people_of_another_account_cannot_be_linked(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    bob = User(email="bob@example.org", password_hash="not-a-real-hash", display_name="Bob")
    session.add(bob)
    await session.flush()
    bobs_sister = Person(owner_id=bob.id, name="Bobs Schwester")
    session.add(bobs_sister)
    await session.flush()
    lena = await create_person(client, "Lena")
    wedding = (await client.post(OCCASIONS, json=WEDDING)).json()

    # An own person next to the foreign one does not get linked either.
    body = {**WEDDING, "name": "Geändert", "person_ids": [lena, str(bobs_sister.id)]}
    url = OCCASIONS if method == "POST" else f"{OCCASIONS}/{wedding['id']}"
    r = await client.request(method, url, json=body)
    assert r.status_code == 404
    assert r.json()["title"] == "Not Found"

    assert (await client.get(OCCASIONS)).json()["items"] == [wedding]


@pytest.mark.requirement("F-03", "F-04")
async def test_birthday_occasion_cannot_be_linked_to_people(
    client: AsyncClient, anna: User
) -> None:
    # A person's birthday lives in person.birthday only, so it cannot be stored twice.
    lena = await create_person(client, "Lena")
    birthday = {"name": "Geburtstag", "date": "1990-05-01", "recurrence": "yearly"}
    birthday_type = {"occasion_type_id": str(BIRTHDAY_TYPE_ID)}

    r = await client.post(OCCASIONS, json={**birthday, **birthday_type, "person_ids": [lena]})
    assert r.status_code == 422
    # The check spans two fields, so the error points at the whole body.
    assert r.json()["errors"][0]["loc"] == ["body"]
    assert (await client.get(OCCASIONS)).json()["total"] == 0

    linked = (await client.post(OCCASIONS, json={**birthday, "person_ids": [lena]})).json()
    r = await client.put(
        f"{OCCASIONS}/{linked['id']}", json={**birthday, **birthday_type, "person_ids": [lena]}
    )
    assert r.status_code == 422
    assert (await client.get(f"{OCCASIONS}/{linked['id']}")).json() == linked

    # Without people the birthday type stays usable.
    r = await client.post(OCCASIONS, json={**birthday, **birthday_type})
    assert r.status_code == 201


@pytest.mark.requirement("F-04")
async def test_deleting_a_person_unlinks_it(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    lena = await create_person(client, "Lena")
    wedding = (await client.post(OCCASIONS, json={**WEDDING, "person_ids": [lena]})).json()

    assert (await client.delete(f"{PEOPLE}/{lena}")).status_code == 204
    # Each request has its own session in production; drop what this one still holds.
    session.expire_all()

    shown = await client.get(f"{OCCASIONS}/{wedding['id']}")
    assert shown.status_code == 200
    assert shown.json()["people"] == []


@pytest.mark.requirement("F-04")
async def test_deleting_an_occasion_keeps_its_people(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    lena = await create_person(client, "Lena")
    wedding = (await client.post(OCCASIONS, json={**WEDDING, "person_ids": [lena]})).json()
    assert await session.scalar(select(func.count()).select_from(person_occasion)) == 1

    assert (await client.delete(f"{OCCASIONS}/{wedding['id']}")).status_code == 204

    assert (await client.get(f"{PEOPLE}/{lena}")).status_code == 200
    assert await session.scalar(select(func.count()).select_from(person_occasion)) == 0


@pytest.mark.requirement("F-04", "F-17")
async def test_deleting_the_account_deletes_its_person_links(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    lena = await create_person(client, "Lena")
    await client.post(OCCASIONS, json={**WEDDING, "person_ids": [lena]})
    assert await session.scalar(select(func.count()).select_from(person_occasion)) == 1

    assert (await client.delete(ACCOUNT)).status_code == 204
    assert await session.scalar(select(func.count()).select_from(person_occasion)) == 0
