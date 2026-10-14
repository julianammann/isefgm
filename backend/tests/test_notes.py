"""Labelled notes on gift ideas (F-07)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import Gift, Note, User
from tests.accounts import log_in_new_user
from tests.ownership import ITEM_METHODS, assert_invisible_to_other_account

NOTES = "/api/v1/notes"
GIFTS = "/api/v1/gifts"
ACCOUNT = "/api/v1/auth/account"
UNKNOWN_ID = "0192f6a0-0000-7000-8000-000000000000"


@pytest.fixture
async def anna(client: AsyncClient, session: AsyncSession) -> User:
    return await log_in_new_user(client, session, "anna@example.org")


async def create_gift(client: AsyncClient, title: str = "Pullover") -> str:
    return (await client.post(GIFTS, json={"title": title})).json()["id"]


async def create_note(client: AsyncClient, gift: str, label: str, text: str = "Notiz") -> str:
    body = {"gift_id": gift, "label": label, "text": text}
    return (await client.post(NOTES, json=body)).json()["id"]


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
async def test_create_and_show_note(client: AsyncClient, anna: User) -> None:
    pullover = await create_gift(client)

    r = await client.post(NOTES, json={"gift_id": pullover, "label": "Größe", "text": "M"})
    assert r.status_code == 201
    created = r.json()
    assert created["gift_id"] == pullover
    assert created["label"] == "Größe"
    assert created["text"] == "M"

    shown = await client.get(f"{NOTES}/{created['id']}")
    assert shown.status_code == 200
    assert shown.json() == created


@pytest.mark.requirement("F-07")
async def test_label_and_text_are_trimmed(client: AsyncClient, anna: User) -> None:
    pullover = await create_gift(client)

    r = await client.post(
        NOTES, json={"gift_id": pullover, "label": "  Größe ", "text": "\n M, eher weit  "}
    )
    assert r.status_code == 201
    assert r.json()["label"] == "Größe"
    assert r.json()["text"] == "M, eher weit"


@pytest.mark.requirement("F-07")
@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"gift_id": None}, "gift_id"),
        ({"gift_id": "not-a-uuid"}, "gift_id"),
        ({"label": None}, "label"),
        ({"label": ""}, "label"),
        ({"label": "   "}, "label"),
        ({"label": "x" * 101}, "label"),
        ({"text": None}, "text"),
        ({"text": ""}, "text"),
        ({"text": "x" * 2001}, "text"),
    ],
)
async def test_invalid_note_is_rejected(
    client: AsyncClient, anna: User, changes: dict[str, object], field: str
) -> None:
    body = {"gift_id": UNKNOWN_ID, "label": "Größe", "text": "M", **changes}

    r = await client.post(NOTES, json=body)
    assert r.status_code == 422
    assert r.json()["errors"][0]["loc"] == ["body", field]


@pytest.mark.requirement("F-07")
async def test_update_replaces_label_and_text(client: AsyncClient, anna: User) -> None:
    pullover = await create_gift(client)
    note = await create_note(client, pullover, "Größe", "M")

    r = await client.put(
        f"{NOTES}/{note}", json={"gift_id": pullover, "label": "Farbe", "text": "dunkelblau"}
    )
    assert r.status_code == 200
    assert r.json() == {"id": note, "gift_id": pullover, "label": "Farbe", "text": "dunkelblau"}
    assert (await client.get(f"{NOTES}/{note}")).json() == r.json()


@pytest.mark.requirement("F-07")
async def test_delete_note(client: AsyncClient, anna: User) -> None:
    pullover = await create_gift(client)
    note = await create_note(client, pullover, "Größe")

    assert (await client.delete(f"{NOTES}/{note}")).status_code == 204
    assert (await client.get(f"{NOTES}/{note}")).status_code == 404
    assert (await client.delete(f"{NOTES}/{note}")).status_code == 404
    # The idea stays.
    assert (await client.get(f"{GIFTS}/{pullover}")).status_code == 200


# --- List (F-07, Q-05) ---------------------------------------------------------


@pytest.mark.requirement("F-07", "Q-05")
async def test_list_filters_by_idea_in_creation_order(client: AsyncClient, anna: User) -> None:
    pullover = await create_gift(client)
    book = await create_gift(client, "Buch")
    size = await create_note(client, pullover, "Größe")
    colour = await create_note(client, pullover, "Farbe")
    await create_note(client, book, "Autorin")

    r = await client.get(NOTES, params={"gift_id": pullover})
    assert r.status_code == 200
    assert [n["id"] for n in r.json()["items"]] == [size, colour]
    assert r.json()["total"] == 2

    assert (await client.get(NOTES)).json()["total"] == 3


@pytest.mark.requirement("F-07", "Q-05")
async def test_list_is_paginated(client: AsyncClient, anna: User) -> None:
    pullover = await create_gift(client)
    for label in ["erste", "zweite", "dritte"]:
        await create_note(client, pullover, label)

    second = await client.get(NOTES, params={"limit": 2, "offset": 2})
    assert [n["label"] for n in second.json()["items"]] == ["dritte"]
    assert second.json()["total"] == 3
    assert second.json()["limit"] == 2
    assert second.json()["offset"] == 2


@pytest.mark.requirement("F-07", "Q-05")
async def test_list_rejects_oversized_page(client: AsyncClient, anna: User) -> None:
    r = await client.get(NOTES, params={"limit": 201})
    assert r.status_code == 422


@pytest.mark.requirement("F-07")
async def test_unknown_or_malformed_id(client: AsyncClient, anna: User) -> None:
    assert (await client.get(f"{NOTES}/{UNKNOWN_ID}")).status_code == 404
    assert (await client.get(f"{NOTES}/not-a-uuid")).status_code == 422


@pytest.mark.requirement("F-07", "Q-01")
async def test_notes_require_login(client: AsyncClient) -> None:
    assert (await client.get(NOTES)).status_code == 401
    body = {"gift_id": UNKNOWN_ID, "label": "Größe", "text": "M"}
    assert (await client.post(NOTES, json=body)).status_code == 401


# --- Tenant separation (Q-01) --------------------------------------------------


@pytest.mark.requirement("F-07", "Q-01")
@pytest.mark.parametrize("method", ITEM_METHODS)
async def test_notes_of_another_account_are_invisible(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    pullover = await create_gift(client)
    note = await create_note(client, pullover, "Größe")

    await assert_invisible_to_other_account(
        client,
        session,
        method=method,
        collection=NOTES,
        item_id=note,
        replacement={"gift_id": pullover, "label": "Hacked", "text": "Hacked"},
    )


@pytest.mark.requirement("F-07", "Q-01")
@pytest.mark.parametrize("method", ["POST", "PUT"])
async def test_note_cannot_go_to_a_foreign_idea(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    foreign = await bobs_gift(session)
    pullover = await create_gift(client)
    note = (
        await client.post(NOTES, json={"gift_id": pullover, "label": "Größe", "text": "M"})
    ).json()

    body = {"gift_id": str(foreign.id), "label": "Geändert", "text": "Geändert"}
    url = NOTES if method == "POST" else f"{NOTES}/{note['id']}"
    r = await client.request(method, url, json=body)
    assert r.status_code == 404
    assert r.json()["title"] == "Not Found"

    assert (await client.get(NOTES)).json()["items"] == [note]


@pytest.mark.requirement("F-07")
async def test_note_on_an_unknown_idea_returns_404(client: AsyncClient, anna: User) -> None:
    r = await client.post(NOTES, json={"gift_id": UNKNOWN_ID, "label": "Größe", "text": "M"})
    assert r.status_code == 404
    assert (await client.get(NOTES)).json()["total"] == 0


@pytest.mark.requirement("F-07", "Q-01")
async def test_filtering_by_a_foreign_idea_shows_nothing(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    foreign = await bobs_gift(session)
    session.add(Note(gift_id=foreign.id, label="Bobs Notiz", text="geheim"))
    await session.flush()

    r = await client.get(NOTES, params={"gift_id": str(foreign.id)})
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 0


# --- Deleting the idea or the account (F-07, F-17) ----------------------------


@pytest.mark.requirement("F-07")
async def test_deleting_the_idea_deletes_its_notes(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    pullover = await create_gift(client)
    note = await create_note(client, pullover, "Größe")

    assert (await client.delete(f"{GIFTS}/{pullover}")).status_code == 204
    # Each request has its own session in production; drop what this one still holds.
    session.expire_all()

    assert (await client.get(f"{NOTES}/{note}")).status_code == 404
    assert await session.scalar(select(func.count()).select_from(Note)) == 0


@pytest.mark.requirement("F-07", "F-17")
async def test_deleting_the_account_deletes_its_notes(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    pullover = await create_gift(client)
    await create_note(client, pullover, "Größe")
    assert await session.scalar(select(func.count()).select_from(Note)) == 1

    assert (await client.delete(ACCOUNT)).status_code == 204
    assert await session.scalar(select(func.count()).select_from(Note)) == 0
