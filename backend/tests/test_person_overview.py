"""Person view: past gifts, ideas, occasions, procurement states and tasks of a person (F-09)."""

import uuid

import pytest
from httpx import AsyncClient
from sqlalchemy import Engine, event
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import User
from tests.accounts import log_in_new_user

PEOPLE = "/api/v1/people"
OCCASIONS = "/api/v1/occasions"
GIFTS = "/api/v1/gifts"
GIFTINGS = "/api/v1/giftings"
TASKS = "/api/v1/tasks"
FIRST_PAGE = {"limit": 50, "offset": 0}


@pytest.fixture
async def anna(client: AsyncClient, session: AsyncSession) -> User:
    return await log_in_new_user(client, session, "anna@example.org")


async def post(client: AsyncClient, url: str, body: dict[str, object]) -> dict[str, object]:
    r = await client.post(url, json=body)
    assert r.status_code == 201, r.text
    return r.json()


def overview(person: dict[str, object]) -> str:
    return f"{PEOPLE}/{person['id']}/overview"


@pytest.mark.requirement("F-09")
async def test_overview_holds_past_gifts_giftings_ideas_occasions_and_tasks_of_the_person(
    client: AsyncClient, anna: User
) -> None:
    lena = await post(client, PEOPLE, {"name": "Lena"})
    max_ = await post(client, PEOPLE, {"name": "Max"})
    xmas = await post(
        client,
        OCCASIONS,
        {
            "name": "Weihnachten",
            "date": "2025-12-24",
            "recurrence": "yearly",
            "person_ids": [lena["id"]],
        },
    )
    await post(
        client,
        OCCASIONS,
        {
            "name": "Hochzeitstag",
            "date": "2019-06-21",
            "recurrence": "yearly",
            "person_ids": [max_["id"]],
        },
    )
    pi = await post(client, GIFTS, {"title": "Raspberry Pi", "person_ids": [lena["id"]]})
    book = await post(client, GIFTS, {"title": "Buch"})
    await post(client, GIFTS, {"title": "Schal", "person_ids": [max_["id"]]})
    tea = await post(client, GIFTS, {"title": "Tee", "person_ids": [lena["id"]]})
    given = await post(
        client,
        GIFTINGS,
        {
            "gift_id": pi["id"],
            "status": "given",
            "person_ids": [lena["id"]],
            "occasion_id": xmas["id"],
            "occasion_date": "2025-12-24",
            "given_on": "2025-12-24",
        },
    )
    planned = await post(
        client,
        GIFTINGS,
        {
            "gift_id": book["id"],
            "status": "planned",
            "person_ids": [lena["id"], max_["id"]],
            "occasion_id": xmas["id"],
            "occasion_date": "2026-12-24",
        },
    )
    idea = await post(client, GIFTINGS, {"gift_id": book["id"], "person_ids": [lena["id"]]})
    await post(
        client, GIFTINGS, {"gift_id": book["id"], "status": "acquired", "person_ids": [max_["id"]]}
    )
    card = await post(client, TASKS, {"gifting_id": given["id"], "title": "Karte schreiben"})
    wrap = await post(
        client, TASKS, {"gifting_id": planned["id"], "title": "Einpacken", "due_on": "2026-12-20"}
    )
    order = await post(
        client, TASKS, {"gifting_id": planned["id"], "title": "Bestellen", "due_on": "2026-12-01"}
    )

    r = await client.get(overview(lena))
    assert r.status_code == 200
    assert r.json() == {
        "given": {"items": [{**given, "tasks": [card]}], "total": 1, **FIRST_PAGE},
        "giftings": {
            "items": [{**planned, "tasks": [order, wrap]}, {**idea, "tasks": []}],
            "total": 2,
            **FIRST_PAGE,
        },
        # The Raspberry Pi was given to Lena, so it is no idea for her any more.
        "ideas": {"items": [tea], "total": 1, **FIRST_PAGE},
        "occasions": {"items": [xmas], "total": 1, **FIRST_PAGE},
    }


@pytest.mark.requirement("F-09")
async def test_ideas_already_used_for_the_person_are_left_out(
    client: AsyncClient, anna: User
) -> None:
    lena = await post(client, PEOPLE, {"name": "Lena"})
    max_ = await post(client, PEOPLE, {"name": "Max"})
    joint = await post(client, GIFTS, {"title": "Buch", "person_ids": [lena["id"]]})
    for_max = await post(client, GIFTS, {"title": "Schal", "person_ids": [lena["id"], max_["id"]]})
    unused = await post(client, GIFTS, {"title": "Tee", "person_ids": [lena["id"]]})
    await post(client, GIFTINGS, {"gift_id": joint["id"], "person_ids": [lena["id"], max_["id"]]})
    await post(client, GIFTINGS, {"gift_id": for_max["id"], "person_ids": [max_["id"]]})

    ideas = (await client.get(overview(lena))).json()["ideas"]
    assert ideas["items"] == [unused, for_max]
    assert ideas["total"] == 2


@pytest.mark.requirement("F-09")
async def test_giftings_come_by_occasion_date_those_without_one_last(
    client: AsyncClient, anna: User
) -> None:
    lena = await post(client, PEOPLE, {"name": "Lena"})
    xmas = await post(
        client, OCCASIONS, {"name": "Weihnachten", "date": "2025-12-24", "recurrence": "yearly"}
    )
    book = await post(client, GIFTS, {"title": "Buch"})
    ids: dict[str, object] = {}
    # Recorded neither in date order nor in reverse date order.
    for occasion_date in ["2025-12-24", None, "2026-12-24"]:
        body: dict[str, object] = {
            "gift_id": book["id"],
            "status": "planned",
            "person_ids": [lena["id"]],
        }
        if occasion_date:
            body |= {"occasion_id": xmas["id"], "occasion_date": occasion_date}
        ids[occasion_date or "none"] = (await post(client, GIFTINGS, body))["id"]

    giftings = (await client.get(overview(lena))).json()["giftings"]["items"]
    assert [g["id"] for g in giftings] == [ids["2025-12-24"], ids["2026-12-24"], ids["none"]]


@pytest.mark.requirement("F-09")
async def test_past_gifts_are_sorted_by_given_date_latest_first(
    client: AsyncClient, anna: User
) -> None:
    lena = await post(client, PEOPLE, {"name": "Lena"})
    xmas = await post(
        client, OCCASIONS, {"name": "Weihnachten", "date": "2024-12-24", "recurrence": "yearly"}
    )
    book = await post(client, GIFTS, {"title": "Buch"})
    ids: list[object] = []
    # Recorded out of order: the later gift first.
    for given_on in ["2025-12-24", "2024-12-24"]:
        gifting = await post(
            client,
            GIFTINGS,
            {
                "gift_id": book["id"],
                "status": "given",
                "person_ids": [lena["id"]],
                "occasion_id": xmas["id"],
                "occasion_date": given_on,
                "given_on": given_on,
            },
        )
        ids.append(gifting["id"])

    given = (await client.get(overview(lena))).json()["given"]["items"]
    assert [g["given_on"] for g in given] == ["2025-12-24", "2024-12-24"]
    assert [g["id"] for g in given] == ids


@pytest.mark.requirement("F-09", "Q-05")
async def test_every_list_is_paginated_with_the_same_limit_and_offset(
    client: AsyncClient, anna: User
) -> None:
    lena = await post(client, PEOPLE, {"name": "Lena"})
    first, second, third = [
        await post(client, GIFTS, {"title": title, "person_ids": [lena["id"]]})
        for title in ["Buch", "Schal", "Tee"]
    ]

    r = await client.get(overview(lena), params={"limit": 2, "offset": 1})
    assert r.status_code == 200
    page = {"limit": 2, "offset": 1}
    assert r.json() == {
        "given": {"items": [], "total": 0, **page},
        "giftings": {"items": [], "total": 0, **page},
        # Newest first, as in the idea list: third, second, first.
        "ideas": {"items": [second, first], "total": 3, **page},
        "occasions": {"items": [], "total": 0, **page},
    }
    assert third not in r.json()["ideas"]["items"]


@pytest.mark.requirement("F-09", "Q-01")
async def test_person_of_another_account_returns_404(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    lena = await post(client, PEOPLE, {"name": "Lena"})
    await post(client, GIFTS, {"title": "Buch", "person_ids": [lena["id"]]})

    await log_in_new_user(client, session, "peter@example.com")
    foreign = await client.get(overview(lena))
    unknown = await client.get(overview({"id": uuid.uuid4()}))

    assert foreign.status_code == 404
    assert foreign.json()["detail"] == "Person not found"
    assert foreign.json() == unknown.json()


@pytest.mark.requirement("F-09", "Q-01")
async def test_overview_requires_login(client: AsyncClient) -> None:
    r = await client.get(overview({"id": uuid.uuid4()}))
    assert r.status_code == 401
    assert r.json()["title"] == "Not authenticated"


async def fill(client: AsyncClient, name: str, n: int) -> dict[str, object]:
    """A person with n occasions, unused ideas, given and planned giftings, each with n tasks."""
    person = await post(client, PEOPLE, {"name": name})
    for i in range(n):
        await post(client, GIFTS, {"title": f"Offene Idee {i}", "person_ids": [person["id"]]})
        occasion = await post(
            client,
            OCCASIONS,
            {
                "name": f"Anlass {i}",
                "date": "2025-12-24",
                "recurrence": "yearly",
                "person_ids": [person["id"]],
            },
        )
        gift = await post(
            client,
            GIFTS,
            {"title": f"Idee {i}", "person_ids": [person["id"]], "occasion_ids": [occasion["id"]]},
        )
        for extra in [{"status": "given", "given_on": "2025-12-24"}, {"status": "planned"}]:
            gifting = await post(
                client,
                GIFTINGS,
                {
                    "gift_id": gift["id"],
                    "person_ids": [person["id"]],
                    "occasion_id": occasion["id"],
                    "occasion_date": "2025-12-24",
                    **extra,
                },
            )
            for j in range(n):
                await post(client, TASKS, {"gifting_id": gifting["id"], "title": f"Aufgabe {j}"})
    return person


@pytest.mark.requirement("F-09", "Q-05")
async def test_number_of_queries_does_not_grow_with_the_rows(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    small = await fill(client, "Lena", 1)
    large = await fill(client, "Max", 4)
    statements: list[str] = []

    def _record(_conn: object, _cursor: object, statement: str, *_: object) -> None:
        statements.append(statement)

    async def count(person: dict[str, object]) -> int:
        # In production every request has a fresh session; nothing may come from the identity map.
        session.expunge_all()
        statements.clear()
        r = await client.get(overview(person))
        assert r.status_code == 200
        return len(statements)

    event.listen(Engine, "before_cursor_execute", _record)
    try:
        small_count = await count(small)
        large_count = await count(large)
    finally:
        event.remove(Engine, "before_cursor_execute", _record)

    # The spy does see the request, so equal counts are no blind spot.
    assert small_count > 0
    assert large_count == small_count
