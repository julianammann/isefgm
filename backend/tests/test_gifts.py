from datetime import date, datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import (
    Gift,
    Occasion,
    Person,
    Recurrence,
    User,
    gift_occasion,
    gift_person,
)
from tests.accounts import log_in_new_user
from tests.ownership import ITEM_METHODS, assert_invisible_to_other_account

GIFTS = "/api/v1/gifts"
PEOPLE = "/api/v1/people"
OCCASIONS = "/api/v1/occasions"
ACCOUNT = "/api/v1/auth/account"
UNKNOWN_ID = "0192f6a0-0000-7000-8000-000000000000"

PI = {
    "title": "Raspberry Pi",
    "description": "Technik, für IT-Begeisterte",
    "price_from": "10.00",
    "price_to": "100.00",
    "currency": "EUR",
    "category": "tech",
}


@pytest.fixture
async def anna(client: AsyncClient, session: AsyncSession) -> User:
    return await log_in_new_user(client, session, "anna@example.org")


async def create_person(client: AsyncClient, name: str) -> str:
    return (await client.post(PEOPLE, json={"name": name})).json()["id"]


async def create_occasion(client: AsyncClient, name: str, on: str) -> str:
    body = {"name": name, "date": on, "recurrence": "yearly"}
    return (await client.post(OCCASIONS, json=body)).json()["id"]


@pytest.mark.requirement("F-05")
async def test_create_and_show_gift(client: AsyncClient, anna: User) -> None:
    r = await client.post(GIFTS, json=PI)
    assert r.status_code == 201
    created = r.json()
    assert created["title"] == "Raspberry Pi"
    assert created["description"] == "Technik, für IT-Begeisterte"
    assert created["price_from"] == "10.00"
    assert created["price_to"] == "100.00"
    assert created["currency"] == "EUR"
    assert created["category"] == "tech"
    assert created["created_at"]

    shown = await client.get(f"{GIFTS}/{created['id']}")
    assert shown.status_code == 200
    assert shown.json() == created


@pytest.mark.requirement("F-05")
async def test_title_alone_creates_a_gift(client: AsyncClient, anna: User) -> None:
    r = await client.post(GIFTS, json={"title": "  Buch  ", "description": "  "})
    assert r.status_code == 201
    body = r.json()
    assert body["title"] == "Buch"
    assert body["description"] is None
    assert body["price_from"] is None
    assert body["price_to"] is None
    assert body["currency"] == "EUR"
    assert body["category"] == "other"


@pytest.mark.requirement("F-05")
async def test_price_range_in_another_currency(client: AsyncClient, anna: User) -> None:
    r = await client.post(GIFTS, json={"title": "Uhr", "price_from": "200", "currency": "CHF"})
    assert r.status_code == 201
    assert r.json()["currency"] == "CHF"


@pytest.mark.requirement("F-05", "Q-08")
async def test_created_at_is_set_by_the_server(client: AsyncClient, anna: User) -> None:
    r = await client.post(GIFTS, json={**PI, "created_at": "2000-01-01T00:00:00Z"})
    assert r.status_code == 201
    created_at = datetime.fromisoformat(r.json()["created_at"])
    assert created_at.year != 2000
    assert created_at.utcoffset() is not None


@pytest.mark.requirement("F-05")
@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"title": ""}, "title"),
        ({"title": "   "}, "title"),
        ({"title": "x" * 201}, "title"),
        ({}, "title"),
        ({"title": "Pi", "description": "x" * 2001}, "description"),
        ({"title": "Pi", "price_from": -1}, "price_from"),
        ({"title": "Pi", "price_from": "19.999"}, "price_from"),
        ({"title": "Pi", "price_to": "abc"}, "price_to"),
        ({"title": "Pi", "price_to": "123456789"}, "price_to"),
        ({"title": "Pi", "currency": "eur"}, "currency"),
        ({"title": "Pi", "currency": "EURO"}, "currency"),
        ({"title": "Pi", "currency": None}, "currency"),
        ({"title": "Pi", "category": "weapons"}, "category"),
        ({"title": "Pi", "category": None}, "category"),
        ({"title": "Pi", "person_ids": None}, "person_ids"),
        ({"title": "Pi", "person_ids": [UNKNOWN_ID] * 101}, "person_ids"),
        ({"title": "Pi", "occasion_ids": UNKNOWN_ID}, "occasion_ids"),
    ],
)
async def test_invalid_gift_is_rejected(
    client: AsyncClient, anna: User, body: dict[str, object], field: str
) -> None:
    r = await client.post(GIFTS, json=body)
    assert r.status_code == 422
    assert r.json()["errors"][0]["loc"] == ["body", field]


@pytest.mark.requirement("F-05")
async def test_price_from_above_price_to_is_rejected(client: AsyncClient, anna: User) -> None:
    r = await client.post(GIFTS, json={"title": "Pi", "price_from": "50", "price_to": "20"})
    assert r.status_code == 422
    # The check spans two fields, so the error points at the whole body.
    assert r.json()["errors"][0]["loc"] == ["body"]


@pytest.mark.requirement("F-05")
@pytest.mark.parametrize(
    "prices",
    [
        {"price_from": "20"},
        {"price_to": "20"},
        {"price_from": "20", "price_to": "20"},
    ],
)
async def test_open_or_equal_price_range_is_accepted(
    client: AsyncClient, anna: User, prices: dict[str, str]
) -> None:
    r = await client.post(GIFTS, json={"title": "Pi", **prices})
    assert r.status_code == 201
    for key in prices:
        assert r.json()[key] == "20.00"


@pytest.mark.requirement("F-05")
@pytest.mark.parametrize(
    ("price_from", "price_to"),
    [
        (Decimal("-1.00"), None),
        (None, Decimal("-1.00")),
        (Decimal("50.00"), Decimal("20.00")),
    ],
)
async def test_database_rejects_invalid_prices(
    session: AsyncSession, anna: User, price_from: Decimal | None, price_to: Decimal | None
) -> None:
    # Bypasses the API: the check constraints hold even if validation is skipped.
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            session.add(
                Gift(owner_id=anna.id, title="Pi", price_from=price_from, price_to=price_to)
            )
            await session.flush()


@pytest.mark.requirement("F-05")
async def test_update_replaces_all_fields(client: AsyncClient, anna: User) -> None:
    created = (await client.post(GIFTS, json={**PI, "currency": "CHF"})).json()

    r = await client.put(f"{GIFTS}/{created['id']}", json={"title": "Raspberry Pi 5"})
    assert r.status_code == 200
    body = r.json()
    assert body["id"] == created["id"]
    assert body["title"] == "Raspberry Pi 5"
    assert body["description"] is None
    assert body["price_from"] is None
    assert body["price_to"] is None
    assert body["currency"] == "EUR"
    assert body["category"] == "other"
    assert body["created_at"] == created["created_at"]


@pytest.mark.requirement("F-05")
async def test_delete_gift(client: AsyncClient, anna: User) -> None:
    created = (await client.post(GIFTS, json=PI)).json()

    assert (await client.delete(f"{GIFTS}/{created['id']}")).status_code == 204
    assert (await client.get(f"{GIFTS}/{created['id']}")).status_code == 404
    assert (await client.delete(f"{GIFTS}/{created['id']}")).status_code == 404


@pytest.mark.requirement("F-05", "Q-05")
async def test_list_is_newest_first_and_paginated(client: AsyncClient, anna: User) -> None:
    for title in ["erste", "zweite", "dritte"]:
        await client.post(GIFTS, json={"title": title})

    first = await client.get(GIFTS, params={"limit": 2, "offset": 0})
    assert first.status_code == 200
    assert [g["title"] for g in first.json()["items"]] == ["dritte", "zweite"]
    assert first.json()["total"] == 3
    assert first.json()["limit"] == 2
    assert first.json()["offset"] == 0

    second = await client.get(GIFTS, params={"limit": 2, "offset": 2})
    assert [g["title"] for g in second.json()["items"]] == ["erste"]
    assert second.json()["total"] == 3


@pytest.mark.requirement("F-05", "Q-05")
async def test_list_rejects_oversized_page(client: AsyncClient, anna: User) -> None:
    r = await client.get(GIFTS, params={"limit": 201})
    assert r.status_code == 422


@pytest.mark.requirement("F-05", "Q-01")
@pytest.mark.parametrize("method", ITEM_METHODS)
async def test_gifts_of_another_account_are_invisible(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    pi = (await client.post(GIFTS, json=PI)).json()

    await assert_invisible_to_other_account(
        client,
        session,
        method=method,
        collection=GIFTS,
        item_id=pi["id"],
        replacement={"title": "Hacked"},
    )


@pytest.mark.requirement("F-05")
async def test_unknown_or_malformed_id(client: AsyncClient, anna: User) -> None:
    assert (await client.get(f"{GIFTS}/0192f6a0-0000-7000-8000-000000000000")).status_code == 404
    assert (await client.get(f"{GIFTS}/not-a-uuid")).status_code == 422


@pytest.mark.requirement("F-05", "Q-01")
async def test_gifts_require_login(client: AsyncClient) -> None:
    assert (await client.get(GIFTS)).status_code == 401
    assert (await client.post(GIFTS, json=PI)).status_code == 401


@pytest.mark.requirement("F-05", "F-17")
async def test_deleting_the_account_deletes_its_gifts(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    await client.post(GIFTS, json=PI)

    assert (await client.delete(ACCOUNT)).status_code == 204
    count = select(func.count()).select_from(Gift).where(Gift.owner_id == anna.id)
    assert await session.scalar(count) == 0


# --- Links to people and occasions (F-04) ------------------------------------


@pytest.mark.requirement("F-04")
async def test_gift_without_people_or_occasions(client: AsyncClient, anna: User) -> None:
    r = await client.post(GIFTS, json={"title": "Buch"})
    assert r.status_code == 201
    assert r.json()["people"] == []
    assert r.json()["occasions"] == []


@pytest.mark.requirement("F-04")
async def test_gift_links_people_and_occasions(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, "Lena")
    anton = await create_person(client, "anton")
    xmas = await create_occasion(client, "Weihnachten", "2026-12-24")
    wedding = await create_occasion(client, "Hochzeitstag", "2019-06-21")

    r = await client.post(
        GIFTS, json={**PI, "person_ids": [lena, anton], "occasion_ids": [xmas, wedding]}
    )
    assert r.status_code == 201
    created = r.json()
    # Same order as the people list (by name) and the occasion list (by date).
    assert created["people"] == [{"id": anton, "name": "anton"}, {"id": lena, "name": "Lena"}]
    assert created["occasions"] == [
        {"id": wedding, "name": "Hochzeitstag"},
        {"id": xmas, "name": "Weihnachten"},
    ]

    assert (await client.get(f"{GIFTS}/{created['id']}")).json() == created
    assert (await client.get(GIFTS)).json()["items"] == [created]


@pytest.mark.requirement("F-04")
async def test_update_replaces_links(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, "Lena")
    anton = await create_person(client, "Anton")
    xmas = await create_occasion(client, "Weihnachten", "2026-12-24")
    body = {**PI, "person_ids": [lena, anton], "occasion_ids": [xmas]}
    created = (await client.post(GIFTS, json=body)).json()

    # occasion_ids left out: a PUT replaces everything, so the occasion is unlinked.
    r = await client.put(f"{GIFTS}/{created['id']}", json={**PI, "person_ids": [anton]})
    assert r.status_code == 200
    assert r.json()["people"] == [{"id": anton, "name": "Anton"}]
    assert r.json()["occasions"] == []
    assert (await client.get(f"{GIFTS}/{created['id']}")).json() == r.json()

    # Unlinking keeps the person and the occasion.
    assert (await client.get(f"{PEOPLE}/{lena}")).status_code == 200
    assert (await client.get(f"{OCCASIONS}/{xmas}")).status_code == 200


@pytest.mark.requirement("F-04")
async def test_links_are_many_to_many(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, "Lena")
    anton = await create_person(client, "Anton")
    xmas = await create_occasion(client, "Weihnachten", "2026-12-24")

    # One idea for several people, as a joint gift or as separate giftings (F-06) ...
    pi = await client.post(GIFTS, json={**PI, "person_ids": [lena, anton], "occasion_ids": [xmas]})
    # ... and one person and one occasion with several ideas.
    book = await client.post(
        GIFTS, json={"title": "Buch", "person_ids": [lena], "occasion_ids": [xmas]}
    )

    assert [p["name"] for p in pi.json()["people"]] == ["Anton", "Lena"]
    assert [p["name"] for p in book.json()["people"]] == ["Lena"]
    assert (
        pi.json()["occasions"] == book.json()["occasions"] == [{"id": xmas, "name": "Weihnachten"}]
    )


@pytest.mark.requirement("F-04")
async def test_repeated_id_is_linked_once(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, "Lena")

    r = await client.post(GIFTS, json={**PI, "person_ids": [lena, lena]})
    assert r.status_code == 201
    assert r.json()["people"] == [{"id": lena, "name": "Lena"}]


@pytest.mark.requirement("F-04")
@pytest.mark.parametrize("field", ["person_ids", "occasion_ids"])
async def test_linking_an_unknown_id_returns_404(
    client: AsyncClient, anna: User, field: str
) -> None:
    r = await client.post(GIFTS, json={**PI, field: [UNKNOWN_ID]})
    assert r.status_code == 404
    assert (await client.get(GIFTS)).json()["total"] == 0


@pytest.mark.requirement("F-04", "Q-01")
@pytest.mark.parametrize("method", ["POST", "PUT"])
@pytest.mark.parametrize("field", ["person_ids", "occasion_ids"])
async def test_records_of_another_account_cannot_be_linked(
    client: AsyncClient, session: AsyncSession, anna: User, method: str, field: str
) -> None:
    bob = User(email="bob@example.org", password_hash="not-a-real-hash", display_name="Bob")
    session.add(bob)
    await session.flush()
    bobs_records = {
        "person_ids": Person(owner_id=bob.id, name="Bobs Schwester"),
        "occasion_ids": Occasion(
            owner_id=bob.id,
            name="Bobs Geburtstag",
            date=date(1990, 5, 1),
            recurrence=Recurrence.YEARLY,
        ),
    }
    session.add(bobs_records[field])
    await session.flush()
    own = await create_person(client, "Lena")
    own_xmas = await create_occasion(client, "Weihnachten", "2026-12-24")
    gift = (await client.post(GIFTS, json=PI)).json()

    # An own record next to the foreign one does not get linked either.
    own_id = own if field == "person_ids" else own_xmas
    body = {**PI, "title": "Geändert", field: [own_id, str(bobs_records[field].id)]}
    url = GIFTS if method == "POST" else f"{GIFTS}/{gift['id']}"
    r = await client.request(method, url, json=body)
    assert r.status_code == 404
    assert r.json()["title"] == "Not Found"

    assert (await client.get(GIFTS)).json()["items"] == [gift]


@pytest.mark.requirement("F-04")
async def test_deleting_a_person_or_occasion_unlinks_it(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    lena = await create_person(client, "Lena")
    xmas = await create_occasion(client, "Weihnachten", "2026-12-24")
    body = {**PI, "person_ids": [lena], "occasion_ids": [xmas]}
    gift = (await client.post(GIFTS, json=body)).json()

    assert (await client.delete(f"{PEOPLE}/{lena}")).status_code == 204
    assert (await client.delete(f"{OCCASIONS}/{xmas}")).status_code == 204
    # Each request has its own session in production; drop what this one still holds.
    session.expire_all()

    shown = await client.get(f"{GIFTS}/{gift['id']}")
    assert shown.status_code == 200
    assert shown.json()["people"] == []
    assert shown.json()["occasions"] == []


@pytest.mark.requirement("F-04")
async def test_deleting_a_gift_keeps_its_people_and_occasions(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    lena = await create_person(client, "Lena")
    xmas = await create_occasion(client, "Weihnachten", "2026-12-24")
    body = {**PI, "person_ids": [lena], "occasion_ids": [xmas]}
    gift = (await client.post(GIFTS, json=body)).json()
    assert await session.scalar(select(func.count()).select_from(gift_person)) == 1

    assert (await client.delete(f"{GIFTS}/{gift['id']}")).status_code == 204

    assert (await client.get(f"{PEOPLE}/{lena}")).status_code == 200
    assert (await client.get(f"{OCCASIONS}/{xmas}")).status_code == 200
    assert await session.scalar(select(func.count()).select_from(gift_person)) == 0
    assert await session.scalar(select(func.count()).select_from(gift_occasion)) == 0


@pytest.mark.requirement("F-04", "F-17")
async def test_deleting_the_account_deletes_its_links(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    lena = await create_person(client, "Lena")
    xmas = await create_occasion(client, "Weihnachten", "2026-12-24")
    await client.post(GIFTS, json={**PI, "person_ids": [lena], "occasion_ids": [xmas]})
    assert await session.scalar(select(func.count()).select_from(gift_occasion)) == 1

    assert (await client.delete(ACCOUNT)).status_code == 204
    assert await session.scalar(select(func.count()).select_from(gift_person)) == 0
    assert await session.scalar(select(func.count()).select_from(gift_occasion)) == 0
