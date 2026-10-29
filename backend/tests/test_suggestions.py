"""Gift suggestions from aggregated features (F-16, Q-04)."""

import asyncio
import uuid
from decimal import Decimal
from typing import Any

import pytest
from httpx import AsyncClient, Cookies
from sqlalchemy import delete, func, select
from sqlalchemy.ext.asyncio import AsyncSession, async_sessionmaker, create_async_engine

from giftmanager.models import Gift, GiftCategory, Note, Person, PriceBand, Suggestion, User
from giftmanager.services import suggestion as suggestion_service
from tests.accounts import log_in_new_user
from tests.ownership import assert_invisible_to_other_account

SUGGESTIONS = "/api/v1/suggestions"
GIFTS = "/api/v1/gifts"
GIFTINGS = "/api/v1/giftings"
PEOPLE = "/api/v1/people"
OCCASIONS = "/api/v1/occasions"
UNKNOWN_ID = "0192f6a0-0000-7000-8000-000000000000"


@pytest.fixture
async def anna(client: AsyncClient, session: AsyncSession) -> User:
    return await log_in_new_user(client, session, "anna@example.org")


async def create_person(client: AsyncClient, name: str = "Lena") -> str:
    return (await client.post(PEOPLE, json={"name": name})).json()["id"]


async def suggest(client: AsyncClient, person: str) -> list[dict[str, Any]]:
    r = await client.post(SUGGESTIONS, json={"person_id": person})
    assert r.status_code == 201
    return r.json()


def features(suggestions: list[dict[str, Any]]) -> list[tuple[Any, Any]]:
    return [(s["category"], s["price_band"]) for s in suggestions]


async def ideas_of_other_accounts(
    session: AsyncSession,
    category: GiftCategory,
    price: str | None,
    *,
    accounts: int = 3,
    per_account: int = 1,
) -> list[User]:
    """Gift ideas of new accounts, created directly, each with a recipient and a note."""
    users: list[User] = []
    for _ in range(accounts):
        user = User(
            email=f"{uuid.uuid4().hex}@example.org",
            password_hash="not-a-real-hash",
            display_name="Fremdes Konto",
        )
        session.add(user)
        await session.flush()
        friend = Person(owner_id=user.id, name="Geheime Person")
        session.add(friend)
        for _ in range(per_account):
            gift = Gift(
                owner_id=user.id,
                title="Geheimer Titel",
                description="Geheime Beschreibung",
                price_from=Decimal(price) if price else None,
                currency="EUR" if price else None,
                category=category,
                people=[friend],
            )
            session.add(gift)
            await session.flush()
            session.add(Note(gift_id=gift.id, label="Geheime Notiz", text="Geheimer Text"))
        await session.flush()
        users.append(user)
    return users


@pytest.mark.requirement("F-16")
async def test_features_shared_by_several_accounts_are_suggested_most_frequent_first(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.BOOKS, "15", accounts=3)
    await ideas_of_other_accounts(session, GiftCategory.EXPERIENCE, "30", per_account=2)
    lena = await create_person(client)

    suggestions = await suggest(client, lena)

    assert features(suggestions) == [("experience", "20_to_50"), ("books", "under_20")]
    assert [s["gift_count"] for s in suggestions] == [6, 3]
    assert {s["target_person_id"] for s in suggestions} == {lena}
    assert {s["status"] for s in suggestions} == {"open"}

    listed = (await client.get(SUGGESTIONS, params={"person_id": lena})).json()
    assert listed["items"] == suggestions
    assert listed["total"] == 2


@pytest.mark.requirement("F-16")
@pytest.mark.parametrize(
    ("price", "band"),
    [
        ("0", "under_20"),
        ("19.99", "under_20"),
        ("20", "20_to_50"),
        ("49.99", "20_to_50"),
        ("50", "50_to_100"),
        ("99.99", "50_to_100"),
        ("100", "over_100"),
        ("100.01", "over_100"),
        (None, None),
    ],
)
async def test_price_band_follows_the_lower_end_of_the_price(
    client: AsyncClient, session: AsyncSession, anna: User, price: str | None, band: str | None
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.TECH, price)
    lena = await create_person(client)

    assert features(await suggest(client, lena)) == [("tech", band)]


@pytest.mark.requirement("F-16", "Q-04")
async def test_features_of_fewer_than_three_accounts_are_not_suggested(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.GAMES, "25", accounts=2, per_account=5)
    lena = await create_person(client)

    assert await suggest(client, lena) == []


@pytest.mark.requirement("F-16", "Q-04")
async def test_own_ideas_do_not_count_towards_the_accounts(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.GAMES, "25", accounts=2)
    lena = await create_person(client)
    tom = await create_person(client, "Tom")
    own = {"title": "Brettspiel", "category": "games", "price_from": "25"}
    for _ in range(3):
        await client.post(GIFTS, json=own | {"person_ids": [tom]})

    assert await suggest(client, lena) == []

    await ideas_of_other_accounts(session, GiftCategory.GAMES, "25", accounts=1)
    assert [s["gift_count"] for s in await suggest(client, lena)] == [3]


@pytest.mark.requirement("F-16")
async def test_category_other_is_never_suggested(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.OTHER, "25", accounts=5)
    lena = await create_person(client)

    assert await suggest(client, lena) == []


@pytest.mark.requirement("F-16", "Q-04")
async def test_suggestions_hold_nothing_of_other_accounts_but_counts(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    others = await ideas_of_other_accounts(session, GiftCategory.FOOD, "12")
    lena = await create_person(client)

    r = await client.post(SUGGESTIONS, json={"person_id": lena})

    assert set(r.json()[0]) == {
        "id",
        "target_person_id",
        "category",
        "price_band",
        "gift_count",
        "status",
        "created_at",
    }
    for secret in ("Geheim", "Fremdes Konto", "example.org", *(str(u.id) for u in others)):
        assert secret not in r.text


@pytest.mark.requirement("F-16")
async def test_features_of_the_persons_ideas_are_left_out(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.BOOKS, "15")
    await ideas_of_other_accounts(session, GiftCategory.EXPERIENCE, "30")
    lena = await create_person(client)
    tom = await create_person(client, "Tom")
    idea = {"title": "Kletterkurs", "category": "experience", "price_from": "45"}
    await client.post(GIFTS, json=idea | {"person_ids": [lena]})

    assert features(await suggest(client, lena)) == [("books", "under_20")]
    assert len(await suggest(client, tom)) == 2


@pytest.mark.requirement("F-16")
async def test_features_of_gifts_the_person_got_are_left_out(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.BOOKS, "15")
    await ideas_of_other_accounts(session, GiftCategory.EXPERIENCE, "30")
    lena = await create_person(client)
    idea = {"title": "Krimi", "category": "books", "price_from": "12"}
    gift = (await client.post(GIFTS, json=idea)).json()["id"]
    xmas = {"name": "Weihnachten", "date": "2025-12-24", "recurrence": "yearly"}
    occasion = (await client.post(OCCASIONS, json=xmas)).json()["id"]
    given = {
        "gift_id": gift,
        "status": "given",
        "person_ids": [lena],
        "occasion_id": occasion,
        "occasion_date": "2025-12-24",
        "given_on": "2025-12-24",
    }
    assert (await client.post(GIFTINGS, json=given)).status_code == 201

    assert features(await suggest(client, lena)) == [("experience", "20_to_50")]


@pytest.mark.requirement("F-16")
async def test_making_suggestions_again_replaces_the_open_ones(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.BOOKS, "15")
    lena = await create_person(client)
    first = await suggest(client, lena)

    second = await suggest(client, lena)

    assert features(second) == features(first)
    assert (await client.get(f"{SUGGESTIONS}/{first[0]['id']}")).status_code == 404
    listed = (await client.get(SUGGESTIONS)).json()
    assert [s["id"] for s in listed["items"]] == [second[0]["id"]]


@pytest.mark.requirement("F-16")
async def test_at_most_five_suggestions(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    for category in list(GiftCategory)[:7]:
        await ideas_of_other_accounts(session, category, "15")
    lena = await create_person(client)

    assert len(await suggest(client, lena)) == 5


@pytest.mark.requirement("F-16")
async def test_accepting_creates_an_idea_for_the_person(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.EXPERIENCE, "30")
    lena = await create_person(client)
    suggestion = (await suggest(client, lena))[0]

    r = await client.post(
        f"{SUGGESTIONS}/{suggestion['id']}/accept", json={"title": "Erlebnis, 20 bis 50 €"}
    )

    assert r.status_code == 201
    gift = r.json()
    assert gift["title"] == "Erlebnis, 20 bis 50 €"
    assert gift["category"] == "experience"
    assert (gift["price_from"], gift["price_to"], gift["currency"]) == ("20.00", "50.00", "EUR")
    assert [p["id"] for p in gift["people"]] == [lena]
    assert (await client.get(f"{GIFTS}/{gift['id']}")).json() == gift
    shown = (await client.get(f"{SUGGESTIONS}/{suggestion['id']}")).json()
    assert shown["status"] == "accepted"
    assert (await client.get(SUGGESTIONS)).json()["total"] == 0
    assert await suggest(client, lena) == []


@pytest.mark.requirement("F-16")
@pytest.mark.parametrize(
    ("price", "price_from", "price_to", "currency"),
    [("150", "100.00", None, "EUR"), (None, None, None, None)],
)
async def test_accepted_idea_gets_the_price_range_of_the_band(
    client: AsyncClient,
    session: AsyncSession,
    anna: User,
    price: str | None,
    price_from: str | None,
    price_to: str | None,
    currency: str | None,
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.TECH, price)
    lena = await create_person(client)
    suggestion = (await suggest(client, lena))[0]

    r = await client.post(f"{SUGGESTIONS}/{suggestion['id']}/accept", json={"title": "Technik"})

    gift = r.json()
    assert (gift["price_from"], gift["price_to"], gift["currency"]) == (
        price_from,
        price_to,
        currency,
    )


@pytest.mark.requirement("F-16")
@pytest.mark.parametrize("band", ["under_20", "20_to_50", "50_to_100", "over_100"])
async def test_accepted_idea_stays_in_the_band_of_its_suggestion(
    client: AsyncClient, session: AsyncSession, anna: User, band: str
) -> None:
    for price in ("15", "30", "75", "150"):
        await ideas_of_other_accounts(session, GiftCategory.TECH, price)
    lena = await create_person(client)
    suggestion = next(s for s in await suggest(client, lena) if s["price_band"] == band)

    await client.post(f"{SUGGESTIONS}/{suggestion['id']}/accept", json={"title": "Technik"})

    left = {s["price_band"] for s in await suggest(client, lena)}
    assert left == {"under_20", "20_to_50", "50_to_100", "over_100"} - {band}


@pytest.mark.requirement("F-16")
async def test_dismissed_suggestion_is_never_made_again(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.BOOKS, "15")
    await ideas_of_other_accounts(session, GiftCategory.EXPERIENCE, "30", per_account=2)
    lena = await create_person(client)
    tom = await create_person(client, "Tom")
    experience = (await suggest(client, lena))[0]

    r = await client.post(f"{SUGGESTIONS}/{experience['id']}/dismiss")

    assert r.status_code == 200
    assert r.json() == experience | {"status": "dismissed"}
    listed = (await client.get(SUGGESTIONS, params={"person_id": lena})).json()
    assert features(listed["items"]) == [("books", "under_20")]
    assert features(await suggest(client, lena)) == [("books", "under_20")]
    assert len(await suggest(client, tom)) == 2


@pytest.mark.requirement("F-16")
@pytest.mark.parametrize("first", ["accept", "dismiss"])
@pytest.mark.parametrize("then", ["accept", "dismiss"])
async def test_only_open_suggestions_can_be_accepted_or_dismissed(
    client: AsyncClient, session: AsyncSession, anna: User, first: str, then: str
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.BOOKS, "15")
    lena = await create_person(client)
    url = f"{SUGGESTIONS}/{(await suggest(client, lena))[0]['id']}"
    await client.post(f"{url}/{first}", json={"title": "Buch"})

    r = await client.post(f"{url}/{then}", json={"title": "Buch"})

    assert r.status_code == 409
    assert (await client.get(GIFTS)).json()["total"] == (1 if first == "accept" else 0)


@pytest.mark.requirement("F-16")
async def test_accepting_twice_at_once_creates_one_idea(database_url: str) -> None:
    engine = create_async_engine(database_url)
    maker = async_sessionmaker(engine, expire_on_commit=False)
    async with maker() as s, s.begin():
        user = User(
            email=f"{uuid.uuid4().hex}@example.org",
            password_hash="not-a-real-hash",
            display_name="Doppelklick",
        )
        s.add(user)
        await s.flush()
        lena = Person(owner_id=user.id, name="Lena")
        s.add(lena)
        await s.flush()
        suggestion = Suggestion(
            owner_id=user.id,
            target_person_id=lena.id,
            category=GiftCategory.BOOKS,
            price_band=PriceBand.UNDER_20,
            gift_count=3,
        )
        s.add(suggestion)

    async def accept() -> Gift:
        async with maker() as s, s.begin():
            return await suggestion_service.accept_suggestion(
                s, user.id, suggestion.id, title="Buch"
            )

    try:
        results = await asyncio.gather(accept(), accept(), return_exceptions=True)
        async with maker() as s:
            ideas = await s.scalar(
                select(func.count()).select_from(Gift).where(Gift.owner_id == user.id)
            )
    finally:
        async with maker() as s, s.begin():
            await s.execute(delete(User).where(User.id == user.id))
        await engine.dispose()

    assert sorted(type(r).__name__ for r in results) == ["ConflictError", "Gift"]
    assert ideas == 1


@pytest.mark.requirement("F-16")
@pytest.mark.parametrize("title", ["", "   ", "x" * 201])
async def test_accepting_needs_a_valid_title(
    client: AsyncClient, session: AsyncSession, anna: User, title: str
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.BOOKS, "15")
    lena = await create_person(client)
    suggestion = (await suggest(client, lena))[0]

    r = await client.post(f"{SUGGESTIONS}/{suggestion['id']}/accept", json={"title": title})

    assert r.status_code == 422
    shown = (await client.get(f"{SUGGESTIONS}/{suggestion['id']}")).json()
    assert shown["status"] == "open"


@pytest.mark.requirement("F-16")
async def test_deleting_the_person_deletes_their_suggestions(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.BOOKS, "15")
    lena = await create_person(client)
    suggestion = (await suggest(client, lena))[0]

    assert (await client.delete(f"{PEOPLE}/{lena}")).status_code == 204

    assert (await client.get(f"{SUGGESTIONS}/{suggestion['id']}")).status_code == 404


@pytest.mark.requirement("F-16", "Q-01")
async def test_suggestions_of_another_account_are_invisible(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.BOOKS, "15")
    lena = await create_person(client)
    suggestion = (await suggest(client, lena))[0]

    await assert_invisible_to_other_account(
        client,
        session,
        method="GET",
        collection=SUGGESTIONS,
        item_id=suggestion["id"],
        replacement={},
    )


@pytest.mark.requirement("F-16", "Q-01")
@pytest.mark.parametrize("action", ["accept", "dismiss"])
async def test_suggestion_of_another_account_cannot_be_accepted_or_dismissed(
    client: AsyncClient, session: AsyncSession, anna: User, action: str
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.BOOKS, "15")
    lena = await create_person(client)
    url = f"{SUGGESTIONS}/{(await suggest(client, lena))[0]['id']}"
    owner_cookies = Cookies(client.cookies)
    await log_in_new_user(client, session, "peter@example.com")

    r = await client.post(f"{url}/{action}", json={"title": "Buch"})

    assert r.status_code == 404
    assert r.json()["title"] == "Not Found"
    assert (await client.get(GIFTS)).json()["total"] == 0
    client.cookies = owner_cookies
    assert (await client.get(url)).json()["status"] == "open"


@pytest.mark.requirement("F-16", "Q-01")
async def test_no_suggestions_for_a_person_of_another_account(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    await ideas_of_other_accounts(session, GiftCategory.BOOKS, "15")
    lena = await create_person(client)
    await log_in_new_user(client, session, "peter@example.com")

    r = await client.post(SUGGESTIONS, json={"person_id": lena})

    assert r.status_code == 404
    listed = (await client.get(SUGGESTIONS, params={"person_id": lena})).json()
    assert listed == {"items": [], "total": 0, "limit": 50, "offset": 0}


@pytest.mark.requirement("F-16", "Q-01")
@pytest.mark.parametrize(
    ("method", "path"),
    [
        ("POST", ""),
        ("GET", ""),
        ("GET", f"/{UNKNOWN_ID}"),
        ("POST", f"/{UNKNOWN_ID}/accept"),
        ("POST", f"/{UNKNOWN_ID}/dismiss"),
    ],
)
async def test_suggestions_require_login(client: AsyncClient, method: str, path: str) -> None:
    body = {"person_id": UNKNOWN_ID, "title": "Buch"}

    r = await client.request(method, f"{SUGGESTIONS}{path}", json=body)

    assert r.status_code == 401


@pytest.mark.requirement("F-16")
@pytest.mark.parametrize("path", [f"/{UNKNOWN_ID}", f"/{UNKNOWN_ID}/dismiss"])
async def test_unknown_suggestion_returns_404(client: AsyncClient, anna: User, path: str) -> None:
    method = "POST" if path.endswith("dismiss") else "GET"

    r = await client.request(method, f"{SUGGESTIONS}{path}")

    assert r.status_code == 404
