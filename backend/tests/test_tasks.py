"""Tasks of a gifting (F-08)."""

import pytest
from httpx import AsyncClient
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import Gift, Gifting, Task, User
from tests.accounts import log_in_new_user
from tests.ownership import ITEM_METHODS, assert_invisible_to_other_account

TASKS = "/api/v1/tasks"
GIFTINGS = "/api/v1/giftings"
GIFTS = "/api/v1/gifts"
PEOPLE = "/api/v1/people"
OCCASIONS = "/api/v1/occasions"
ACCOUNT = "/api/v1/auth/account"
UNKNOWN_ID = "0192f6a0-0000-7000-8000-000000000000"


@pytest.fixture
async def anna(client: AsyncClient, session: AsyncSession) -> User:
    return await log_in_new_user(client, session, "anna@example.org")


async def create_gifting(client: AsyncClient, title: str = "Raspberry Pi") -> str:
    """A new gift idea and a gifting of it, in status `idea`."""
    gift = (await client.post(GIFTS, json={"title": title})).json()["id"]
    return (await client.post(GIFTINGS, json={"gift_id": gift})).json()["id"]


async def create_task(
    client: AsyncClient, gifting: str, title: str, due_on: str | None = None
) -> str:
    body = {"gifting_id": gifting, "title": title, "due_on": due_on}
    return (await client.post(TASKS, json=body)).json()["id"]


async def bobs_gifting(session: AsyncSession) -> Gifting:
    """A gifting of another account, created directly."""
    bob = User(email="bob@example.org", password_hash="not-a-real-hash", display_name="Bob")
    session.add(bob)
    await session.flush()
    gift = Gift(owner_id=bob.id, title="Bobs Idee")
    session.add(gift)
    await session.flush()
    gifting = Gifting(gift_id=gift.id)
    session.add(gifting)
    await session.flush()
    return gifting


# --- Create, show, update, delete (F-08) --------------------------------------


@pytest.mark.requirement("F-08")
async def test_create_and_show_task(client: AsyncClient, anna: User) -> None:
    pi = await create_gifting(client)

    r = await client.post(
        TASKS,
        json={
            "gifting_id": pi,
            "title": "Netzteil dazu bestellen",
            "status": "in_progress",
            "due_on": "2026-12-01",
        },
    )
    assert r.status_code == 201
    created = r.json()
    assert created["gifting_id"] == pi
    assert created["title"] == "Netzteil dazu bestellen"
    assert created["status"] == "in_progress"
    assert created["due_on"] == "2026-12-01"
    assert created["created_at"]

    shown = await client.get(f"{TASKS}/{created['id']}")
    assert shown.status_code == 200
    assert shown.json() == created


@pytest.mark.requirement("F-08")
async def test_gifting_and_title_alone_create_an_open_task(client: AsyncClient, anna: User) -> None:
    pi = await create_gifting(client)

    r = await client.post(TASKS, json={"gifting_id": pi, "title": "Geschenkpapier kaufen"})
    assert r.status_code == 201
    assert r.json()["status"] == "open"
    assert r.json()["due_on"] is None


@pytest.mark.requirement("F-08")
@pytest.mark.parametrize("gifting_status", ["idea", "planned", "acquired", "given"])
async def test_tasks_can_be_added_from_the_idea_phase_on(
    client: AsyncClient, anna: User, gifting_status: str
) -> None:
    gift = (await client.post(GIFTS, json={"title": "Raspberry Pi"})).json()["id"]
    body: dict[str, object] = {"gift_id": gift, "status": gifting_status}
    if gifting_status == "given":
        lena = (await client.post(PEOPLE, json={"name": "Lena"})).json()["id"]
        xmas = {"name": "Weihnachten", "date": "2025-12-24", "recurrence": "yearly"}
        occasion = (await client.post(OCCASIONS, json=xmas)).json()["id"]
        body |= {
            "person_ids": [lena],
            "occasion_id": occasion,
            "occasion_date": "2025-12-24",
            "given_on": "2025-12-24",
        }
    gifting = (await client.post(GIFTINGS, json=body)).json()
    assert gifting["status"] == gifting_status

    r = await client.post(TASKS, json={"gifting_id": gifting["id"], "title": "Karte schreiben"})
    assert r.status_code == 201


@pytest.mark.requirement("F-08")
async def test_status_can_change_in_any_direction(client: AsyncClient, anna: User) -> None:
    pi = await create_gifting(client)
    task = await create_task(client, pi, "Netzteil dazu bestellen")

    for status in ["in_progress", "done", "discarded", "open", "done"]:
        body = {"gifting_id": pi, "title": "Netzteil dazu bestellen", "status": status}
        r = await client.put(f"{TASKS}/{task}", json=body)
        assert r.status_code == 200
        assert r.json()["status"] == status
        assert (await client.get(f"{TASKS}/{task}")).json()["status"] == status


@pytest.mark.requirement("F-08")
async def test_title_is_trimmed(client: AsyncClient, anna: User) -> None:
    pi = await create_gifting(client)

    r = await client.post(TASKS, json={"gifting_id": pi, "title": "  Karte schreiben \n"})
    assert r.status_code == 201
    assert r.json()["title"] == "Karte schreiben"


@pytest.mark.requirement("F-08")
@pytest.mark.parametrize(
    ("changes", "field"),
    [
        ({"gifting_id": None}, "gifting_id"),
        ({"gifting_id": "not-a-uuid"}, "gifting_id"),
        ({"title": None}, "title"),
        ({"title": ""}, "title"),
        ({"title": "   "}, "title"),
        ({"title": "x" * 201}, "title"),
        ({"status": None}, "status"),
        ({"status": "closed"}, "status"),
        ({"due_on": "2026-13-01"}, "due_on"),
        ({"due_on": "morgen"}, "due_on"),
    ],
)
async def test_invalid_task_is_rejected(
    client: AsyncClient, anna: User, changes: dict[str, object], field: str
) -> None:
    body = {"gifting_id": UNKNOWN_ID, "title": "Karte schreiben", **changes}

    r = await client.post(TASKS, json=body)
    assert r.status_code == 422
    assert r.json()["errors"][0]["loc"] == ["body", field]


@pytest.mark.requirement("F-08")
async def test_update_replaces_all_fields(client: AsyncClient, anna: User) -> None:
    pi = await create_gifting(client)
    book = await create_gifting(client, "Buch")
    created = (
        await client.post(
            TASKS,
            json={"gifting_id": pi, "title": "Netzteil", "status": "open", "due_on": "2026-12-01"},
        )
    ).json()

    r = await client.put(
        f"{TASKS}/{created['id']}",
        json={"gifting_id": book, "title": "Einpacken", "status": "done"},
    )
    assert r.status_code == 200
    assert r.json() == {
        "id": created["id"],
        "gifting_id": book,
        "title": "Einpacken",
        "status": "done",
        # Left out in a full update means: no due date any more.
        "due_on": None,
        "created_at": created["created_at"],
    }
    assert (await client.get(f"{TASKS}/{created['id']}")).json() == r.json()


@pytest.mark.requirement("F-08")
async def test_delete_task(client: AsyncClient, anna: User) -> None:
    pi = await create_gifting(client)
    task = await create_task(client, pi, "Karte schreiben")

    assert (await client.delete(f"{TASKS}/{task}")).status_code == 204
    assert (await client.get(f"{TASKS}/{task}")).status_code == 404
    assert (await client.delete(f"{TASKS}/{task}")).status_code == 404
    # The gifting stays.
    assert (await client.get(f"{GIFTINGS}/{pi}")).status_code == 200


# --- List (F-08, Q-05) ---------------------------------------------------------


@pytest.mark.requirement("F-08", "Q-05")
async def test_list_is_ordered_by_due_date_then_creation(client: AsyncClient, anna: User) -> None:
    pi = await create_gifting(client)
    wrap = await create_task(client, pi, "Einpacken", "2026-12-20")
    card = await create_task(client, pi, "Karte schreiben")
    order = await create_task(client, pi, "Bestellen", "2026-12-01")
    ribbon = await create_task(client, pi, "Schleife kaufen", "2026-12-20")

    r = await client.get(TASKS)
    assert r.status_code == 200
    assert [t["id"] for t in r.json()["items"]] == [order, wrap, ribbon, card]


@pytest.mark.requirement("F-08", "Q-05")
async def test_list_filters_by_gifting(client: AsyncClient, anna: User) -> None:
    pi = await create_gifting(client)
    book = await create_gifting(client, "Buch")
    order = await create_task(client, pi, "Bestellen")
    wrap = await create_task(client, pi, "Einpacken")
    await create_task(client, book, "Signieren lassen")

    r = await client.get(TASKS, params={"gifting_id": pi})
    assert r.status_code == 200
    assert [t["id"] for t in r.json()["items"]] == [order, wrap]
    assert r.json()["total"] == 2

    assert (await client.get(TASKS)).json()["total"] == 3


@pytest.mark.requirement("F-08", "Q-05")
async def test_list_is_paginated(client: AsyncClient, anna: User) -> None:
    pi = await create_gifting(client)
    for title in ["erste", "zweite", "dritte"]:
        await create_task(client, pi, title)

    second = await client.get(TASKS, params={"limit": 2, "offset": 2})
    assert [t["title"] for t in second.json()["items"]] == ["dritte"]
    assert second.json()["total"] == 3
    assert second.json()["limit"] == 2
    assert second.json()["offset"] == 2


@pytest.mark.requirement("F-08", "Q-05")
async def test_list_rejects_oversized_page(client: AsyncClient, anna: User) -> None:
    r = await client.get(TASKS, params={"limit": 201})
    assert r.status_code == 422


@pytest.mark.requirement("F-08")
async def test_unknown_or_malformed_id(client: AsyncClient, anna: User) -> None:
    assert (await client.get(f"{TASKS}/{UNKNOWN_ID}")).status_code == 404
    assert (await client.get(f"{TASKS}/not-a-uuid")).status_code == 422


@pytest.mark.requirement("F-08", "Q-01")
async def test_tasks_require_login(client: AsyncClient) -> None:
    assert (await client.get(TASKS)).status_code == 401
    body = {"gifting_id": UNKNOWN_ID, "title": "Karte schreiben"}
    assert (await client.post(TASKS, json=body)).status_code == 401


# --- Tenant separation (Q-01) --------------------------------------------------


@pytest.mark.requirement("F-08", "Q-01")
@pytest.mark.parametrize("method", ITEM_METHODS)
async def test_tasks_of_another_account_are_invisible(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    pi = await create_gifting(client)
    task = await create_task(client, pi, "Karte schreiben")

    await assert_invisible_to_other_account(
        client,
        session,
        method=method,
        collection=TASKS,
        item_id=task,
        replacement={"gifting_id": pi, "title": "Hacked", "status": "discarded"},
    )


@pytest.mark.requirement("F-08", "Q-01")
@pytest.mark.parametrize("method", ["POST", "PUT"])
async def test_task_cannot_go_to_a_foreign_gifting(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    foreign = await bobs_gifting(session)
    pi = await create_gifting(client)
    task = (await client.post(TASKS, json={"gifting_id": pi, "title": "Karte schreiben"})).json()

    body = {"gifting_id": str(foreign.id), "title": "Geändert"}
    url = TASKS if method == "POST" else f"{TASKS}/{task['id']}"
    r = await client.request(method, url, json=body)
    assert r.status_code == 404
    assert r.json()["title"] == "Not Found"

    assert (await client.get(TASKS)).json()["items"] == [task]


@pytest.mark.requirement("F-08")
async def test_task_on_an_unknown_gifting_returns_404(client: AsyncClient, anna: User) -> None:
    r = await client.post(TASKS, json={"gifting_id": UNKNOWN_ID, "title": "Karte schreiben"})
    assert r.status_code == 404
    assert (await client.get(TASKS)).json()["total"] == 0


@pytest.mark.requirement("F-08", "Q-01")
async def test_filtering_by_a_foreign_gifting_shows_nothing(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    foreign = await bobs_gifting(session)
    session.add(Task(gifting_id=foreign.id, title="Bobs Aufgabe"))
    await session.flush()

    r = await client.get(TASKS, params={"gifting_id": str(foreign.id)})
    assert r.status_code == 200
    assert r.json()["items"] == []
    assert r.json()["total"] == 0


# --- Deleting the gifting or the account (F-08, F-17) -------------------------


@pytest.mark.requirement("F-08")
async def test_deleting_the_gifting_deletes_its_tasks(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    pi = await create_gifting(client)
    task = await create_task(client, pi, "Karte schreiben")

    assert (await client.delete(f"{GIFTINGS}/{pi}")).status_code == 204
    # Each request has its own session in production; drop what this one still holds.
    session.expire_all()

    assert (await client.get(f"{TASKS}/{task}")).status_code == 404
    assert await session.scalar(select(func.count()).select_from(Task)) == 0


@pytest.mark.requirement("F-08", "F-17")
async def test_deleting_the_account_deletes_its_tasks(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    pi = await create_gifting(client)
    await create_task(client, pi, "Karte schreiben")
    assert await session.scalar(select(func.count()).select_from(Task)) == 1

    assert (await client.delete(ACCOUNT)).status_code == 204
    assert await session.scalar(select(func.count()).select_from(Task)) == 0
