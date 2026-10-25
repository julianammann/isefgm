"""Read-only share links on chosen people (F-14)."""

from datetime import timedelta
from typing import Any

import pytest
from httpx import AsyncClient, Cookies
from sqlalchemy import func, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core.security import hash_session_token
from giftmanager.models import Person, ShareLink, User
from tests.accounts import log_in_new_user
from tests.conftest import FixedClock
from tests.ownership import ITEM_METHODS, assert_invisible_to_other_account

SHARE_LINKS = "/api/v1/share-links"
SHARED = "/api/v1/shared"
PEOPLE = "/api/v1/people"
GIFTS = "/api/v1/gifts"
LINKS = "/api/v1/links"
NOTES = "/api/v1/notes"
ACCOUNT = "/api/v1/auth/account"
UNKNOWN_ID = "0192f6a0-0000-7000-8000-000000000000"
THALIA = "https://www.thalia.de/shop/home/artikeldetails/A1234"


@pytest.fixture
async def anna(client: AsyncClient, session: AsyncSession, clock: FixedClock) -> User:
    return await log_in_new_user(client, session, "anna@example.org")


async def create_person(client: AsyncClient, name: str, **fields: object) -> str:
    return (await client.post(PEOPLE, json={"name": name, **fields})).json()["id"]


async def create_gift(client: AsyncClient, title: str, people: list[str], **fields: object) -> str:
    body = {"title": title, "person_ids": people, **fields}
    return (await client.post(GIFTS, json=body)).json()["id"]


async def share(client: AsyncClient, people: list[str], **fields: object) -> Any:
    r = await client.post(SHARE_LINKS, json={"person_ids": people, **fields})
    assert r.status_code == 201
    return r.json()


async def open_shared(client: AsyncClient, token: str) -> Any:
    client.cookies.clear()
    r = await client.get(f"{SHARED}/{token}")
    assert r.status_code == 200
    return r.json()


@pytest.mark.requirement("F-14", "Q-03")
async def test_create_returns_the_token_once(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    lena = await create_person(client, "Lena")

    created = await share(client, [lena])
    assert created["people"] == [{"id": lena, "name": "Lena"}]
    assert created["active"] is True
    assert created["expires_at"] is None
    token = created["token"]
    assert isinstance(token, str)
    assert len(token) >= 43

    shown = await client.get(f"{SHARE_LINKS}/{created['id']}")
    assert shown.status_code == 200
    assert "token" not in shown.json()
    assert shown.json() == {k: v for k, v in created.items() if k != "token"}
    listed = (await client.get(SHARE_LINKS)).json()["items"]
    assert all("token" not in item for item in listed)

    stored = await session.scalar(select(ShareLink.token_hash))
    assert stored == hash_session_token(token)
    assert stored != token


@pytest.mark.requirement("F-14", "Q-03")
async def test_every_link_gets_its_own_token(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, "Lena")

    first = await share(client, [lena])
    second = await share(client, [lena])
    assert first["token"] != second["token"]


@pytest.mark.requirement("F-14")
@pytest.mark.parametrize(
    ("body", "field"),
    [
        ({"person_ids": []}, "person_ids"),
        ({}, "person_ids"),
        ({"person_ids": ["not-a-uuid"]}, "person_ids"),
        ({"person_ids": [UNKNOWN_ID], "expires_at": "2026-12-24T23:59:59"}, "expires_at"),
        ({"person_ids": [UNKNOWN_ID], "expires_at": "morgen"}, "expires_at"),
        ({"person_ids": [UNKNOWN_ID], "active": "vielleicht"}, "active"),
    ],
)
async def test_invalid_share_link_is_rejected(
    client: AsyncClient, anna: User, body: dict[str, object], field: str
) -> None:
    r = await client.post(SHARE_LINKS, json=body)
    assert r.status_code == 422
    assert r.json()["errors"][0]["loc"][:2] == ["body", field]


@pytest.mark.requirement("F-14")
async def test_expiry_in_the_past_is_rejected(
    client: AsyncClient, anna: User, clock: FixedClock
) -> None:
    lena = await create_person(client, "Lena")

    past = (clock.now() - timedelta(minutes=1)).isoformat()
    r = await client.post(SHARE_LINKS, json={"person_ids": [lena], "expires_at": past})
    assert r.status_code == 400
    assert (await client.get(SHARE_LINKS)).json()["total"] == 0


@pytest.mark.requirement("F-14")
async def test_update_replaces_people_expiry_and_active(
    client: AsyncClient, anna: User, clock: FixedClock
) -> None:
    lena = await create_person(client, "Lena")
    max_ = await create_person(client, "Max")
    created = await share(client, [lena])

    expires = (clock.now() + timedelta(days=7)).isoformat()
    body = {"person_ids": [max_, lena], "expires_at": expires, "active": False}
    r = await client.put(f"{SHARE_LINKS}/{created['id']}", json=body)
    assert r.status_code == 200
    updated = r.json()
    assert [p["name"] for p in updated["people"]] == ["Lena", "Max"]
    assert updated["active"] is False
    assert updated["expires_at"] == "2026-01-08T12:00:00Z"
    assert (await client.get(f"{SHARE_LINKS}/{created['id']}")).json() == updated


@pytest.mark.requirement("F-14")
async def test_unchanged_past_expiry_does_not_block_an_update(
    client: AsyncClient, anna: User, clock: FixedClock
) -> None:
    lena = await create_person(client, "Lena")
    max_ = await create_person(client, "Max")
    expires = (clock.now() + timedelta(days=1)).isoformat()
    created = await share(client, [lena], expires_at=expires)
    clock.advance(timedelta(days=2))

    body = {"person_ids": [lena, max_], "expires_at": expires, "active": True}
    assert (await client.put(f"{SHARE_LINKS}/{created['id']}", json=body)).status_code == 200

    body["expires_at"] = (clock.now() - timedelta(hours=1)).isoformat()
    assert (await client.put(f"{SHARE_LINKS}/{created['id']}", json=body)).status_code == 400


@pytest.mark.requirement("F-14")
async def test_delete_share_link(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, "Lena")
    created = await share(client, [lena])

    assert (await client.delete(f"{SHARE_LINKS}/{created['id']}")).status_code == 204
    assert (await client.get(f"{SHARE_LINKS}/{created['id']}")).status_code == 404
    assert (await client.delete(f"{SHARE_LINKS}/{created['id']}")).status_code == 404
    assert (await client.get(f"{PEOPLE}/{lena}")).status_code == 200

    client.cookies.clear()
    assert (await client.get(f"{SHARED}/{created['token']}")).status_code == 404


@pytest.mark.requirement("F-14", "Q-05")
async def test_list_is_newest_first_and_paginated(client: AsyncClient, anna: User) -> None:
    lena = await create_person(client, "Lena")
    ids = [(await share(client, [lena]))["id"] for _ in range(3)]

    first = (await client.get(SHARE_LINKS, params={"limit": 2})).json()
    assert [item["id"] for item in first["items"]] == ids[::-1][:2]
    assert first["total"] == 3
    second = (await client.get(SHARE_LINKS, params={"limit": 2, "offset": 2})).json()
    assert [item["id"] for item in second["items"]] == [ids[0]]


@pytest.mark.requirement("F-14", "Q-01")
async def test_share_links_require_login(client: AsyncClient) -> None:
    assert (await client.get(SHARE_LINKS)).status_code == 401
    assert (await client.post(SHARE_LINKS, json={"person_ids": [UNKNOWN_ID]})).status_code == 401


@pytest.mark.requirement("F-14", "Q-01")
@pytest.mark.parametrize("method", ITEM_METHODS)
async def test_share_links_of_another_account_are_invisible(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    lena = await create_person(client, "Lena")
    created = await share(client, [lena])

    await assert_invisible_to_other_account(
        client,
        session,
        method=method,
        collection=SHARE_LINKS,
        item_id=str(created["id"]),
        replacement={"person_ids": [lena], "active": False},
    )


@pytest.mark.requirement("F-14", "Q-01")
@pytest.mark.parametrize("method", ["POST", "PUT"])
async def test_foreign_person_cannot_be_shared(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    lena = await create_person(client, "Lena")
    created = await share(client, [lena])
    bob = User(email="bob@example.org", password_hash="not-a-real-hash", display_name="Bob")
    session.add(bob)
    await session.flush()
    foreign = Person(owner_id=bob.id, name="Bobs Schwester")
    session.add(foreign)
    await session.flush()

    body = {"person_ids": [lena, str(foreign.id)]}
    url = SHARE_LINKS if method == "POST" else f"{SHARE_LINKS}/{created['id']}"
    r = await client.request(method, url, json=body)
    assert r.status_code == 404

    listed = (await client.get(SHARE_LINKS)).json()
    assert listed["total"] == 1
    assert listed["items"][0]["people"] == [{"id": lena, "name": "Lena"}]


@pytest.mark.requirement("F-14", "Q-01")
async def test_shared_view_shows_only_the_chosen_people_and_their_ideas(
    client: AsyncClient, anna: User
) -> None:
    lena = await create_person(
        client, "Lena", birthday="1994-03-17", relationship="Schwester", notes="Größe M"
    )
    max_ = await create_person(client, "Max")
    tom = await create_person(client, "Tom")
    older = await create_gift(client, "Buch", [lena])
    await client.post(LINKS, json={"gift_id": older, "label": "Thalia", "url": THALIA})
    await client.post(NOTES, json={"gift_id": older, "label": "Größe", "text": "M"})
    await create_gift(
        client,
        "Raspberry Pi",
        [lena, max_],
        description="Technik",
        price_from="10",
        price_to="100",
        category="tech",
    )
    await create_gift(client, "Geheim", [tom])
    await create_gift(client, "Ohne Person", [])
    created = await share(client, [max_, lena])

    shared = await open_shared(client, created["token"])
    assert shared == {
        "owner_name": "anna@example.org",
        "expires_at": None,
        "people": [
            {
                "name": "Lena",
                "gifts": [
                    {
                        "title": "Raspberry Pi",
                        "description": "Technik",
                        "price_from": "10.00",
                        "price_to": "100.00",
                        "currency": "EUR",
                        "category": "tech",
                        "links": [],
                        "images": [],
                    },
                    {
                        "title": "Buch",
                        "description": None,
                        "price_from": None,
                        "price_to": None,
                        "currency": None,
                        "category": "other",
                        "links": [{"label": "Thalia", "url": THALIA}],
                        "images": [],
                    },
                ],
            },
            {
                "name": "Max",
                "gifts": [
                    {
                        "title": "Raspberry Pi",
                        "description": "Technik",
                        "price_from": "10.00",
                        "price_to": "100.00",
                        "currency": "EUR",
                        "category": "tech",
                        "links": [],
                        "images": [],
                    }
                ],
            },
        ],
    }
    text = str(shared)
    for hidden in ("1994-03-17", "Schwester", "Größe", "Tom", "Geheim", "Ohne Person", lena):
        assert hidden not in text


@pytest.mark.requirement("F-14")
async def test_person_without_ideas_is_shown_with_an_empty_list(
    client: AsyncClient, anna: User
) -> None:
    lena = await create_person(client, "Lena")
    created = await share(client, [lena])

    shared = await open_shared(client, created["token"])
    assert shared["people"] == [{"name": "Lena", "gifts": []}]


@pytest.mark.requirement("F-14", "Q-01")
@pytest.mark.parametrize("token", ["unbekannt", "q3Xb2k9VtL0mR8sY1nWc4eJ7uA5hZ6oP-dFgQiKjTx0"])
async def test_unknown_token_returns_404(client: AsyncClient, token: str) -> None:
    r = await client.get(f"{SHARED}/{token}")
    assert r.status_code == 404
    assert r.json()["detail"] == "Share link not found"


@pytest.mark.requirement("F-14", "Q-01")
async def test_hash_of_a_token_does_not_open_the_link(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    lena = await create_person(client, "Lena")
    await share(client, [lena])
    stored = await session.scalar(select(ShareLink.token_hash))

    client.cookies.clear()
    assert (await client.get(f"{SHARED}/{stored}")).status_code == 404


@pytest.mark.requirement("F-14")
async def test_expired_link_returns_404(client: AsyncClient, anna: User, clock: FixedClock) -> None:
    lena = await create_person(client, "Lena")
    expires = clock.now() + timedelta(days=1)
    created = await share(client, [lena], expires_at=expires.isoformat())

    shared = await open_shared(client, created["token"])
    assert shared["expires_at"] == "2026-01-02T12:00:00Z"

    clock.advance(timedelta(days=1) - timedelta(seconds=1))
    assert (await client.get(f"{SHARED}/{created['token']}")).status_code == 200
    clock.advance(timedelta(seconds=1))
    r = await client.get(f"{SHARED}/{created['token']}")
    assert r.status_code == 404
    assert r.json()["detail"] == "Share link not found"


@pytest.mark.requirement("F-14")
async def test_deactivated_link_returns_404_until_reactivated(
    client: AsyncClient, anna: User
) -> None:
    lena = await create_person(client, "Lena")
    created = await share(client, [lena])
    owner_cookies = Cookies(client.cookies)
    url = f"{SHARE_LINKS}/{created['id']}"

    off = {"person_ids": [lena], "active": False}
    assert (await client.put(url, json=off)).status_code == 200
    client.cookies.clear()
    r = await client.get(f"{SHARED}/{created['token']}")
    assert r.status_code == 404
    assert r.json()["detail"] == "Share link not found"

    client.cookies = owner_cookies
    assert (await client.put(url, json={**off, "active": True})).status_code == 200
    await open_shared(client, created["token"])


@pytest.mark.requirement("F-14", "Q-01")
@pytest.mark.parametrize("method", ["POST", "PUT", "PATCH", "DELETE"])
async def test_shared_view_is_read_only(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    lena = await create_person(client, "Lena")
    await create_gift(client, "Buch", [lena])
    created = await share(client, [lena])
    before = await open_shared(client, created["token"])

    r = await client.request(method, f"{SHARED}/{created['token']}", json={"name": "Hacked"})
    assert r.status_code == 405

    assert await open_shared(client, created["token"]) == before
    assert await session.scalar(select(func.count()).select_from(ShareLink)) == 1


@pytest.mark.requirement("F-14", "Q-01")
async def test_shared_view_follows_later_changes(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    lena = await create_person(client, "Lena")
    max_ = await create_person(client, "Max")
    created = await share(client, [lena, max_])
    owner_cookies = Cookies(client.cookies)
    await create_gift(client, "Buch", [lena])

    assert (await client.delete(f"{PEOPLE}/{max_}")).status_code == 204
    session.expire_all()

    shared = await open_shared(client, created["token"])
    assert [p["name"] for p in shared["people"]] == ["Lena"]
    assert [g["title"] for g in shared["people"][0]["gifts"]] == ["Buch"]

    client.cookies = owner_cookies
    assert (await client.get(f"{SHARE_LINKS}/{created['id']}")).json()["people"] == [
        {"id": lena, "name": "Lena"}
    ]


@pytest.mark.requirement("F-14", "F-17")
async def test_deleting_the_account_deletes_its_share_links(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    lena = await create_person(client, "Lena")
    created = await share(client, [lena])

    assert (await client.delete(ACCOUNT)).status_code == 204
    assert await session.scalar(select(func.count()).select_from(ShareLink)) == 0
    client.cookies.clear()
    assert (await client.get(f"{SHARED}/{created['token']}")).status_code == 404
