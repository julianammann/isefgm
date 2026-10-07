import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import Person, User
from tests.accounts import log_in_new_user
from tests.ownership import ITEM_METHODS, assert_invisible_to_other_account

PEOPLE = "/api/v1/people"
ACCOUNT = "/api/v1/auth/account"

LENA = {
    "name": "Lena",
    "birthday": "1994-03-17",
    "relationship": "Schwester",
    "notes": "Mag Bouldern",
}


@pytest.fixture
async def anna(client: AsyncClient, session: AsyncSession) -> User:
    return await log_in_new_user(client, session, "anna@example.org")


@pytest.mark.requirement("F-02")
async def test_create_and_show_person(client: AsyncClient, anna: User) -> None:
    r = await client.post(PEOPLE, json=LENA)
    assert r.status_code == 201
    created = r.json()
    assert created["name"] == "Lena"
    assert created["birthday"] == "1994-03-17"
    assert created["relationship"] == "Schwester"
    assert created["notes"] == "Mag Bouldern"
    assert created["created_at"]

    shown = await client.get(f"{PEOPLE}/{created['id']}")
    assert shown.status_code == 200
    assert shown.json() == created


@pytest.mark.requirement("F-02")
async def test_only_name_is_required_and_blank_fields_become_null(
    client: AsyncClient, anna: User
) -> None:
    r = await client.post(PEOPLE, json={"name": "  Tom  ", "relationship": "  ", "notes": ""})
    assert r.status_code == 201
    body = r.json()
    assert body["name"] == "Tom"
    assert body["birthday"] is None
    assert body["relationship"] is None
    assert body["notes"] is None


@pytest.mark.requirement("F-02")
@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"name": ""}, "name"),
        ({"name": "   "}, "name"),
        ({"name": "x" * 101}, "name"),
        ({}, "name"),
        ({"name": "Lena", "birthday": "17.03.1994"}, "birthday"),
        ({"name": "Lena", "birthday": "1994-03-17T10:00:00Z"}, "birthday"),
        ({"name": "Lena", "relationship": "x" * 101}, "relationship"),
        ({"name": "Lena", "notes": "x" * 2001}, "notes"),
    ],
)
async def test_invalid_person_is_rejected(
    client: AsyncClient, anna: User, body: dict[str, str], field: str
) -> None:
    r = await client.post(PEOPLE, json=body)
    assert r.status_code == 422
    assert r.json()["errors"][0]["loc"] == ["body", field]


@pytest.mark.requirement("F-02")
async def test_update_replaces_all_fields(client: AsyncClient, anna: User) -> None:
    created = (await client.post(PEOPLE, json=LENA)).json()

    r = await client.put(f"{PEOPLE}/{created['id']}", json={"name": "Lena M."})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == created["id"]
    assert body["name"] == "Lena M."
    assert body["birthday"] is None
    assert body["relationship"] is None
    assert body["notes"] is None
    assert body["created_at"] == created["created_at"]


@pytest.mark.requirement("F-02")
async def test_delete_person(client: AsyncClient, anna: User) -> None:
    created = (await client.post(PEOPLE, json=LENA)).json()

    assert (await client.delete(f"{PEOPLE}/{created['id']}")).status_code == 204
    assert (await client.get(f"{PEOPLE}/{created['id']}")).status_code == 404
    assert (await client.delete(f"{PEOPLE}/{created['id']}")).status_code == 404


@pytest.mark.requirement("F-02", "Q-05")
async def test_list_is_sorted_by_name_and_paginated(client: AsyncClient, anna: User) -> None:
    for name in ["carla", "Anton", "bea"]:
        await client.post(PEOPLE, json={"name": name})

    first = await client.get(PEOPLE, params={"limit": 2, "offset": 0})
    assert first.status_code == 200
    assert [p["name"] for p in first.json()["items"]] == ["Anton", "bea"]
    assert first.json()["total"] == 3
    assert first.json()["limit"] == 2
    assert first.json()["offset"] == 0

    second = await client.get(PEOPLE, params={"limit": 2, "offset": 2})
    assert [p["name"] for p in second.json()["items"]] == ["carla"]
    assert second.json()["total"] == 3


@pytest.mark.requirement("F-02", "Q-05")
async def test_list_rejects_oversized_page(client: AsyncClient, anna: User) -> None:
    r = await client.get(PEOPLE, params={"limit": 201})
    assert r.status_code == 422


@pytest.mark.requirement("F-02", "Q-01")
@pytest.mark.parametrize("method", ITEM_METHODS)
async def test_people_of_another_account_are_invisible(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    lena = (await client.post(PEOPLE, json=LENA)).json()

    await assert_invisible_to_other_account(
        client,
        session,
        method=method,
        collection=PEOPLE,
        item_id=lena["id"],
        replacement={"name": "Hacked"},
    )


@pytest.mark.requirement("F-02")
async def test_unknown_or_malformed_id(client: AsyncClient, anna: User) -> None:
    assert (await client.get(f"{PEOPLE}/0192f6a0-0000-7000-8000-000000000000")).status_code == 404
    assert (await client.get(f"{PEOPLE}/not-a-uuid")).status_code == 422


@pytest.mark.requirement("F-02", "Q-01")
async def test_people_require_login(client: AsyncClient) -> None:
    assert (await client.get(PEOPLE)).status_code == 401
    assert (await client.post(PEOPLE, json=LENA)).status_code == 401


@pytest.mark.requirement("F-02", "F-17")
async def test_deleting_the_account_deletes_its_people(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    await client.post(PEOPLE, json=LENA)

    assert (await client.delete(ACCOUNT)).status_code == 204
    count = select(func.count()).select_from(Person).where(Person.owner_id == anna.id)
    assert await session.scalar(count) == 0
