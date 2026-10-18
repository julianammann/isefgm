"""Complete list of people, gift ideas and past gifts (F-15)."""

import pytest
from httpx import AsyncClient
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import User
from tests.accounts import log_in_new_user

FULL_LIST = "/api/v1/full-list"
PEOPLE = "/api/v1/people"
OCCASIONS = "/api/v1/occasions"
GIFTS = "/api/v1/gifts"
GIFTINGS = "/api/v1/giftings"
LINKS = "/api/v1/links"
NOTES = "/api/v1/notes"
THALIA = "https://www.thalia.de/shop/home/artikeldetails/A1234"


@pytest.fixture
async def anna(client: AsyncClient, session: AsyncSession) -> User:
    return await log_in_new_user(client, session, "anna@example.org")


async def post(client: AsyncClient, url: str, body: dict[str, object]) -> dict[str, object]:
    r = await client.post(url, json=body)
    assert r.status_code == 201, r.text
    return r.json()


@pytest.mark.requirement("F-15")
async def test_empty_account_gets_empty_lists(client: AsyncClient, anna: User) -> None:
    r = await client.get(FULL_LIST)
    assert r.status_code == 200
    assert r.json() == {"people": [], "gifts": [], "given": []}


@pytest.mark.requirement("F-15")
async def test_list_holds_people_ideas_and_past_gifts(client: AsyncClient, anna: User) -> None:
    max_ = await post(client, PEOPLE, {"name": "Max"})
    lena = await post(
        client, PEOPLE, {"name": "Lena", "birthday": "1994-03-17", "relationship": "Schwester"}
    )
    xmas = await post(
        client, OCCASIONS, {"name": "Weihnachten 2025", "date": "2025-12-24", "recurrence": "none"}
    )
    pi = await post(
        client,
        GIFTS,
        {
            "title": "Raspberry Pi",
            "price_from": "10",
            "price_to": "100",
            "category": "tech",
            "person_ids": [lena["id"], max_["id"]],
            "occasion_ids": [xmas["id"]],
        },
    )
    book = await post(client, GIFTS, {"title": "Buch"})
    thalia = await post(client, LINKS, {"gift_id": book["id"], "label": "Thalia", "url": THALIA})
    note = await post(
        client, NOTES, {"gift_id": book["id"], "label": "Format", "text": "Taschenbuch"}
    )
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
    await post(client, GIFTINGS, {"gift_id": book["id"], "status": "planned"})

    r = await client.get(FULL_LIST)
    assert r.status_code == 200
    full_list = r.json()
    assert full_list["people"] == [lena, max_]
    assert full_list["gifts"] == [
        {**book, "links": [thalia], "notes": [note]},
        {**pi, "links": [], "notes": []},
    ]
    assert full_list["given"] == [given]


@pytest.mark.requirement("F-15")
async def test_past_gifts_are_only_given_ones_latest_first(client: AsyncClient, anna: User) -> None:
    lena = await post(client, PEOPLE, {"name": "Lena"})
    xmas = await post(
        client, OCCASIONS, {"name": "Weihnachten", "date": "2024-12-24", "recurrence": "yearly"}
    )
    book = await post(client, GIFTS, {"title": "Buch", "person_ids": [lena["id"]]})
    ids: dict[str, object] = {}
    for status, given_on in [("given", "2024-12-24"), ("given", "2025-12-24"), ("acquired", None)]:
        body: dict[str, object] = {"gift_id": book["id"], "status": status}
        if given_on:
            body |= {
                "person_ids": [lena["id"]],
                "occasion_id": xmas["id"],
                "occasion_date": given_on,
                "given_on": given_on,
            }
        ids[given_on or status] = (await post(client, GIFTINGS, body))["id"]

    given = (await client.get(FULL_LIST)).json()["given"]
    assert [g["id"] for g in given] == [ids["2025-12-24"], ids["2024-12-24"]]
    assert all(g["status"] == "given" for g in given)


@pytest.mark.requirement("F-15", "Q-01")
async def test_list_shows_nothing_of_another_account(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    lena = await post(client, PEOPLE, {"name": "Lena"})
    xmas = await post(
        client, OCCASIONS, {"name": "Weihnachten", "date": "2025-12-24", "recurrence": "none"}
    )
    book = await post(client, GIFTS, {"title": "Buch", "person_ids": [lena["id"]]})
    await post(client, LINKS, {"gift_id": book["id"], "label": "Thalia", "url": THALIA})
    await post(client, NOTES, {"gift_id": book["id"], "label": "Format", "text": "Taschenbuch"})
    await post(
        client,
        GIFTINGS,
        {
            "gift_id": book["id"],
            "status": "given",
            "person_ids": [lena["id"]],
            "occasion_id": xmas["id"],
            "occasion_date": "2025-12-24",
            "given_on": "2025-12-24",
        },
    )
    assert (await client.get(FULL_LIST)).json()["given"] != []

    await log_in_new_user(client, session, "peter@example.com")
    r = await client.get(FULL_LIST)
    assert r.status_code == 200
    assert r.json() == {"people": [], "gifts": [], "given": []}


@pytest.mark.requirement("F-15", "Q-01")
async def test_list_requires_login(client: AsyncClient) -> None:
    r = await client.get(FULL_LIST)
    assert r.status_code == 401
    assert r.headers["content-type"] == "application/json"
    assert r.json()["title"] == "Not authenticated"
