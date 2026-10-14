"""Labelled links on gift ideas (F-07)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import Attachment, AttachmentKind, Gift, User
from tests.accounts import log_in_new_user
from tests.ownership import ITEM_METHODS, assert_invisible_to_other_account

LINKS = "/api/v1/links"
GIFTS = "/api/v1/gifts"
ACCOUNT = "/api/v1/auth/account"
UNKNOWN_ID = "0192f6a0-0000-7000-8000-000000000000"
THALIA = "https://www.thalia.de/shop/home/artikeldetails/A1234?ref=wunschliste#details"


@pytest.fixture
async def anna(client: AsyncClient, session: AsyncSession) -> User:
    return await log_in_new_user(client, session, "anna@example.org")


async def create_gift(client: AsyncClient, title: str = "Buch") -> str:
    return (await client.post(GIFTS, json={"title": title})).json()["id"]


async def create_link(client: AsyncClient, gift: str, label: str, url: str = THALIA) -> str:
    body = {"gift_id": gift, "label": label, "url": url}
    return (await client.post(LINKS, json=body)).json()["id"]


async def bobs_gift(session: AsyncSession) -> Gift:
    """A gift idea of another account, created directly."""
    bob = User(email="bob@example.org", password_hash="not-a-real-hash", display_name="Bob")
    session.add(bob)
    await session.flush()
    gift = Gift(owner_id=bob.id, title="Bobs Idee")
    session.add(gift)
    await session.flush()
    return gift


# --- Create, show, update, delete (F-07) --------------------------------------


@pytest.mark.requirement("F-07")
async def test_create_and_show_link(client: AsyncClient, anna: User) -> None:
    book = await create_gift(client)

    r = await client.post(LINKS, json={"gift_id": book, "label": "Thalia", "url": THALIA})
    assert r.status_code == 201
    created = r.json()
    assert created["gift_id"] == book
    assert created["label"] == "Thalia"
    # Stored as entered: path, query and fragment unchanged.
    assert created["url"] == THALIA

    shown = await client.get(f"{LINKS}/{created['id']}")
    assert shown.status_code == 200
    assert shown.json() == created


@pytest.mark.requirement("F-07")
@pytest.mark.parametrize(
    "url",
    [
        "http://example.org/buch",
        "https://example.org",
        "https://shop.example.org:8443/a/b?c=d",
        "  https://example.org/mit-leerzeichen  ",
    ],
)
async def test_http_and_https_urls_are_accepted(client: AsyncClient, anna: User, url: str) -> None:
    book = await create_gift(client)

    r = await client.post(LINKS, json={"gift_id": book, "label": "Shop", "url": url})
    assert r.status_code == 201
    assert r.json()["url"] == url.strip()


@pytest.mark.requirement("F-07")
@pytest.mark.parametrize(
    "url",
    [
        "",
        "   ",
        "thalia",
        "www.thalia.de/buch",
        "/shop/buch",
        "https://",
        "javascript:alert(1)",
        "data:text/html,<script>alert(1)</script>",
        "ftp://example.org/datei",
        "mailto:anna@example.org",
        "file:///etc/passwd",
        "https://example.org/" + "a" * 2048,
    ],
)
async def test_invalid_url_is_rejected(client: AsyncClient, anna: User, url: str) -> None:
    # The frontend renders the URL as a link, so only web addresses may get through.
    r = await client.post(LINKS, json={"gift_id": UNKNOWN_ID, "label": "Shop", "url": url})
    assert r.status_code == 422
    assert r.json()["errors"][0]["loc"] == ["body", "url"]


@pytest.mark.requirement("F-07")
@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"gift_id": None}, "gift_id"),
        ({"gift_id": "not-a-uuid"}, "gift_id"),
        ({"label": None}, "label"),
        ({"label": "  "}, "label"),
        ({"label": "x" * 101}, "label"),
        ({"url": None}, "url"),
    ],
)
async def test_invalid_link_is_rejected(
    client: AsyncClient, anna: User, changes: dict[str, object], field: str
) -> None:
    body = {"gift_id": UNKNOWN_ID, "label": "Thalia", "url": THALIA, **changes}

    r = await client.post(LINKS, json=body)
    assert r.status_code == 422
    assert r.json()["errors"][0]["loc"] == ["body", field]


@pytest.mark.requirement("F-07")
async def test_update_replaces_label_and_url(client: AsyncClient, anna: User) -> None:
    book = await create_gift(client)
    link = await create_link(client, book, "Thalia")

    body = {"gift_id": book, "label": "Verlag", "url": "https://example.org/verlag"}
    r = await client.put(f"{LINKS}/{link}", json=body)
    assert r.status_code == 200
    assert r.json() == {"id": link, **body}
    assert (await client.get(f"{LINKS}/{link}")).json() == r.json()


@pytest.mark.requirement("F-07")
async def test_update_rejects_an_invalid_url(client: AsyncClient, anna: User) -> None:
    book = await create_gift(client)
    link = await create_link(client, book, "Thalia")

    body = {"gift_id": book, "label": "Thalia", "url": "javascript:alert(1)"}
    assert (await client.put(f"{LINKS}/{link}", json=body)).status_code == 422
    assert (await client.get(f"{LINKS}/{link}")).json()["url"] == THALIA


@pytest.mark.requirement("F-07")
async def test_delete_link(client: AsyncClient, anna: User) -> None:
    book = await create_gift(client)
    link = await create_link(client, book, "Thalia")

    assert (await client.delete(f"{LINKS}/{link}")).status_code == 204
    assert (await client.get(f"{LINKS}/{link}")).status_code == 404
    assert (await client.delete(f"{LINKS}/{link}")).status_code == 404
    # The idea stays.
    assert (await client.get(f"{GIFTS}/{book}")).status_code == 200


# --- List (F-07, Q-05) ---------------------------------------------------------


@pytest.mark.requirement("F-07", "Q-05")
async def test_list_filters_by_idea_in_creation_order(client: AsyncClient, anna: User) -> None:
    book = await create_gift(client)
    pi = await create_gift(client, "Raspberry Pi")
    thalia = await create_link(client, book, "Thalia")
    publisher = await create_link(client, book, "Verlag", "https://example.org/verlag")
    await create_link(client, pi, "Shop", "https://example.org/pi")

    r = await client.get(LINKS, params={"gift_id": book})
    assert r.status_code == 200
    assert [link["id"] for link in r.json()["items"]] == [thalia, publisher]
    assert r.json()["total"] == 2

    assert (await client.get(LINKS)).json()["total"] == 3


@pytest.mark.requirement("F-07", "Q-05")
async def test_list_is_paginated(client: AsyncClient, anna: User) -> None:
    book = await create_gift(client)
    for label in ["erste", "zweite", "dritte"]:
        await create_link(client, book, label)

    second = await client.get(LINKS, params={"limit": 2, "offset": 2})
    assert [link["label"] for link in second.json()["items"]] == ["dritte"]
    assert second.json()["total"] == 3
    assert second.json()["limit"] == 2
    assert second.json()["offset"] == 2


@pytest.mark.requirement("F-07", "Q-05")
async def test_list_rejects_oversized_page(client: AsyncClient, anna: User) -> None:
    r = await client.get(LINKS, params={"limit": 201})
    assert r.status_code == 422


@pytest.mark.requirement("F-07")
async def test_unknown_or_malformed_id(client: AsyncClient, anna: User) -> None:
    assert (await client.get(f"{LINKS}/{UNKNOWN_ID}")).status_code == 404
    assert (await client.get(f"{LINKS}/not-a-uuid")).status_code == 422


@pytest.mark.requirement("F-07", "Q-01")
async def test_links_require_login(client: AsyncClient) -> None:
    assert (await client.get(LINKS)).status_code == 401
    body = {"gift_id": UNKNOWN_ID, "label": "Thalia", "url": THALIA}
    assert (await client.post(LINKS, json=body)).status_code == 401


# --- Tenant separation (Q-01) --------------------------------------------------


@pytest.mark.requirement("F-07", "Q-01")
@pytest.mark.parametrize("method", ITEM_METHODS)
async def test_links_of_another_account_are_invisible(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    book = await create_gift(client)
    link = await create_link(client, book, "Thalia")

    await assert_invisible_to_other_account(
        client,
        session,
        method=method,
        collection=LINKS,
        item_id=link,
        replacement={"gift_id": book, "label": "Hacked", "url": "https://example.org/hacked"},
    )


@pytest.mark.requirement("F-07", "Q-01")
@pytest.mark.parametrize("method", ["POST", "PUT"])
async def test_link_cannot_go_to_a_foreign_idea(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    foreign = await bobs_gift(session)
    book = await create_gift(client)
    link = (
        await client.post(LINKS, json={"gift_id": book, "label": "Thalia", "url": THALIA})
    ).json()

    body = {"gift_id": str(foreign.id), "label": "Geändert", "url": "https://example.org/x"}
    url = LINKS if method == "POST" else f"{LINKS}/{link['id']}"
    r = await client.request(method, url, json=body)
    assert r.status_code == 404
    assert r.json()["title"] == "Not Found"

    assert (await client.get(LINKS)).json()["items"] == [link]


@pytest.mark.requirement("F-07")
async def test_link_on_an_unknown_idea_returns_404(client: AsyncClient, anna: User) -> None:
    r = await client.post(LINKS, json={"gift_id": UNKNOWN_ID, "label": "Thalia", "url": THALIA})
    assert r.status_code == 404
    assert (await client.get(LINKS)).json()["total"] == 0


@pytest.mark.requirement("F-07", "Q-01")
async def test_filtering_by_a_foreign_idea_shows_nothing(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    foreign = await bobs_gift(session)
    session.add(
        Attachment(gift_id=foreign.id, kind=AttachmentKind.LINK, label="Bobs Link", url=THALIA)
    )
    await session.flush()

    r = await client.get(LINKS, params={"gift_id": str(foreign.id)})
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 0


# --- Database rules, deleting the idea or the account (F-07, F-17) ------------


@pytest.mark.requirement("F-07")
async def test_database_requires_a_url_for_a_link(session: AsyncSession, anna: User) -> None:
    # Bypasses the API: ck_attachment_link_has_url holds even if validation is skipped.
    gift = Gift(owner_id=anna.id, title="Buch")
    session.add(gift)
    await session.flush()

    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            session.add(Attachment(gift_id=gift.id, kind=AttachmentKind.LINK, label="Leer"))
            await session.flush()


@pytest.mark.requirement("F-07")
async def test_deleting_the_idea_deletes_its_links(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    book = await create_gift(client)
    link = await create_link(client, book, "Thalia")

    assert (await client.delete(f"{GIFTS}/{book}")).status_code == 204
    # Each request has its own session in production; drop what this one still holds.
    session.expire_all()

    assert (await client.get(f"{LINKS}/{link}")).status_code == 404
    assert await session.scalar(select(func.count()).select_from(Attachment)) == 0


@pytest.mark.requirement("F-07", "F-17")
async def test_deleting_the_account_deletes_its_links(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    book = await create_gift(client)
    await create_link(client, book, "Thalia")
    assert await session.scalar(select(func.count()).select_from(Attachment)) == 1

    assert (await client.delete(ACCOUNT)).status_code == 204
    assert await session.scalar(select(func.count()).select_from(Attachment)) == 0
