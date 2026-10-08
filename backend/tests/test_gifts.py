from datetime import datetime
from decimal import Decimal

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import Gift, User
from tests.accounts import log_in_new_user
from tests.ownership import ITEM_METHODS, assert_invisible_to_other_account

GIFTS = "/api/v1/gifts"
ACCOUNT = "/api/v1/auth/account"

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
    assert body["currency"] is None
    assert body["category"] == "other"


@pytest.mark.requirement("F-05")
async def test_price_without_currency_is_in_euro(client: AsyncClient, anna: User) -> None:
    r = await client.post(GIFTS, json={"title": "Pi", "price_to": "20"})
    assert r.status_code == 201
    assert r.json()["currency"] == "EUR"


@pytest.mark.requirement("F-05")
async def test_currency_without_price_is_not_stored(client: AsyncClient, anna: User) -> None:
    # The form sends its currency field even when both prices are empty.
    r = await client.post(GIFTS, json={"title": "Pi", "currency": "CHF"})
    assert r.status_code == 201
    assert r.json()["currency"] is None


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
        ({"title": "Pi", "category": "weapons"}, "category"),
        ({"title": "Pi", "category": None}, "category"),
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
                Gift(
                    owner_id=anna.id,
                    title="Pi",
                    price_from=price_from,
                    price_to=price_to,
                    currency="EUR",
                )
            )
            await session.flush()


@pytest.mark.requirement("F-05")
@pytest.mark.parametrize(
    ("price_from", "currency"),
    [
        (Decimal("20.00"), None),
        (None, "EUR"),
    ],
)
async def test_database_requires_a_currency_exactly_with_a_price(
    session: AsyncSession, anna: User, price_from: Decimal | None, currency: str | None
) -> None:
    # Bypasses the API: a currency without a price, or a price without one, is never stored.
    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            session.add(
                Gift(owner_id=anna.id, title="Pi", price_from=price_from, currency=currency)
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
    assert body["currency"] is None
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
