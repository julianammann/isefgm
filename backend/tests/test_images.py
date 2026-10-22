"""Labelled images on gift ideas (F-07): upload, delivery and foreign access (Q-01, Q-03)."""

import uuid
from datetime import timedelta
from pathlib import Path
from typing import Any

import pytest
from anyio import CapacityLimiter
from httpx import AsyncClient, Cookies, Response
from sqlalchemy import func, select
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core import imaging
from giftmanager.models import Attachment, AttachmentKind, Gift, User
from giftmanager.services import auth as auth_service
from giftmanager.services import gift as gift_service
from giftmanager.services import image as image_service
from tests.accounts import log_in_new_user
from tests.conftest import FixedClock
from tests.images import make_image, open_image, png_header_only
from tests.ownership import ITEM_METHODS, assert_invisible_to_other_account

# No test may write to the real UPLOADS_DIR.
pytestmark = pytest.mark.usefixtures("uploads_dir")

IMAGES = "/api/v1/images"
GIFTS = "/api/v1/gifts"
LINKS = "/api/v1/links"
PEOPLE = "/api/v1/people"
SHARE_LINKS = "/api/v1/share-links"
SHARED = "/api/v1/shared"
UNKNOWN_ID = "0192f6a0-0000-7000-8000-000000000000"
JPEG = make_image("JPEG")
SVG = b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>'


async def create_gift(client: AsyncClient, title: str = "Buch") -> str:
    return (await client.post(GIFTS, json={"title": title})).json()["id"]


async def upload(
    client: AsyncClient,
    gift: str,
    label: str = "Laden",
    data: bytes = JPEG,
    filename: str = "foto.jpg",
    content_type: str = "image/jpeg",
) -> Response:
    return await client.post(
        IMAGES,
        data={"gift_id": gift, "label": label},
        files={"file": (filename, data, content_type)},
    )


async def create_image(client: AsyncClient, gift: str, label: str = "Laden") -> dict[str, Any]:
    r = await upload(client, gift, label)
    assert r.status_code == 201
    return r.json()


def stored_files(uploads_dir: Path) -> list[Path]:
    return sorted(p for p in uploads_dir.rglob("*") if p.is_file())


async def bobs_gift(session: AsyncSession) -> Gift:
    """A gift idea of another account, created directly."""
    bob = User(email="bob@example.org", password_hash="not-a-real-hash", display_name="Bob")
    session.add(bob)
    await session.flush()
    gift = Gift(owner_id=bob.id, title="Bobs Idee")
    session.add(gift)
    await session.flush()
    return gift


@pytest.fixture
async def anna(client: AsyncClient, session: AsyncSession) -> User:
    return await log_in_new_user(client, session, "anna@example.org")


def file_columns(owner: User, name: str = "a" * 32) -> dict[str, Any]:
    return {
        "storage_path": f"{owner.id}/{name}.webp",
        "mime_type": "image/webp",
        "size_bytes": 1234,
    }


# --- Database rules -----------------------------------------------------------


@pytest.mark.requirement("F-07")
@pytest.mark.parametrize("missing", ["storage_path", "mime_type", "size_bytes"])
async def test_image_without_its_file_is_rejected_by_the_database(
    session: AsyncSession, anna: User, missing: str
) -> None:
    gift = Gift(owner_id=anna.id, title="Buch")
    session.add(gift)
    await session.flush()
    columns = file_columns(anna)
    del columns[missing]

    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            image = Attachment(gift_id=gift.id, kind=AttachmentKind.IMAGE, label="Bild", **columns)
            session.add(image)
            await session.flush()


@pytest.mark.requirement("F-07")
async def test_two_images_cannot_share_a_file(session: AsyncSession, anna: User) -> None:
    gift = Gift(owner_id=anna.id, title="Buch")
    session.add(gift)
    await session.flush()
    session.add(
        Attachment(gift_id=gift.id, kind=AttachmentKind.IMAGE, label="Eins", **file_columns(anna))
    )
    await session.flush()

    with pytest.raises(IntegrityError):
        async with session.begin_nested():
            twin = Attachment(
                gift_id=gift.id, kind=AttachmentKind.IMAGE, label="Zwei", **file_columns(anna)
            )
            session.add(twin)
            await session.flush()


# --- Upload, show, update, delete (F-07) ---------------------------------------


@pytest.mark.requirement("F-07")
async def test_upload_and_show_image(client: AsyncClient, anna: User, uploads_dir: Path) -> None:
    book = await create_gift(client)

    r = await upload(client, book, "Bild vom Laden")
    assert r.status_code == 201
    created = r.json()
    [stored] = stored_files(uploads_dir)
    assert created == {
        "id": created["id"],
        "gift_id": book,
        "label": "Bild vom Laden",
        "mime_type": "image/webp",
        "size_bytes": stored.stat().st_size,
    }

    shown = await client.get(f"{IMAGES}/{created['id']}")
    assert shown.status_code == 200
    assert shown.json() == created


@pytest.mark.requirement("F-07", "Q-01")
async def test_upload_stores_webp_under_the_account(
    client: AsyncClient, anna: User, uploads_dir: Path
) -> None:
    await create_image(client, await create_gift(client))

    [stored] = stored_files(uploads_dir)
    assert stored.parent == uploads_dir / str(anna.id)
    assert open_image(stored.read_bytes()).format == "WEBP"


@pytest.mark.requirement("F-07")
async def test_content_returns_the_stored_file(
    client: AsyncClient, anna: User, uploads_dir: Path
) -> None:
    image = await create_image(client, await create_gift(client))

    r = await client.get(f"{IMAGES}/{image['id']}/content")

    assert r.status_code == 200
    [stored] = stored_files(uploads_dir)
    assert r.content == stored.read_bytes()
    assert r.headers["content-type"] == "image/webp"
    assert r.headers["cache-control"] == "private, no-store"


@pytest.mark.requirement("F-07", "Q-03")
async def test_misleading_name_and_type_are_ignored(client: AsyncClient, anna: User) -> None:
    book = await create_gift(client)

    as_png = await upload(client, book, filename="foto.png", content_type="image/png")
    assert as_png.status_code == 201
    as_jpeg = await upload(client, book, data=SVG, filename="foto.jpg", content_type="image/jpeg")
    assert as_jpeg.status_code == 415


@pytest.mark.requirement("F-07", "Q-03")
@pytest.mark.parametrize(
    ("data", "status", "title"),
    [
        pytest.param(make_image("GIF"), 415, "Unsupported Media Type", id="gif"),
        pytest.param(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n", 415, "Unsupported Media Type", id="pdf"),
        pytest.param(b"hello", 415, "Unsupported Media Type", id="text"),
        pytest.param(b"\xff" * (5 * 1024 * 1024 + 1), 413, "Content Too Large", id="over-5-mb"),
        pytest.param(png_header_only(20000, 20000), 413, "Content Too Large", id="huge-header"),
        pytest.param(
            make_image("WEBP", (4001, 2500)), 413, "Content Too Large", id="webp-over-10-mp"
        ),
    ],
)
async def test_invalid_files_are_rejected(
    client: AsyncClient,
    session: AsyncSession,
    anna: User,
    uploads_dir: Path,
    data: bytes,
    status: int,
    title: str,
) -> None:
    book = await create_gift(client)

    r = await upload(client, book, data=data)

    assert r.status_code == status
    assert r.json()["title"] == title
    assert await session.scalar(select(func.count()).select_from(Attachment)) == 0
    assert stored_files(uploads_dir) == []


@pytest.mark.requirement("F-07")
async def test_image_with_broken_exif_is_accepted(client: AsyncClient, anna: User) -> None:
    broken = make_image("JPEG", (300, 100), exif=b"Exif\x00\x00garbage")

    r = await upload(client, await create_gift(client), data=broken)

    assert r.status_code == 201


@pytest.mark.requirement("F-07")
async def test_busy_upload_returns_503(
    client: AsyncClient, anna: User, monkeypatch: pytest.MonkeyPatch
) -> None:
    book = await create_gift(client)
    full = CapacityLimiter(1)
    full.acquire_on_behalf_of_nowait("flood")
    monkeypatch.setattr(imaging, "_admission_limiter", full)

    r = await upload(client, book)

    assert r.status_code == 503
    assert r.headers["retry-after"] == "5"


@pytest.mark.requirement("F-07")
async def test_sixth_image_is_rejected(client: AsyncClient, anna: User, uploads_dir: Path) -> None:
    book = await create_gift(client)
    for n in range(5):
        await create_image(client, book, f"Bild {n}")

    r = await upload(client, book, "Bild 6")

    assert r.status_code == 409
    assert len(stored_files(uploads_dir)) == 5
    # The limit is per idea: another idea takes images again.
    await create_image(client, await create_gift(client, "Andere Idee"))


@pytest.mark.requirement("F-07")
async def test_label_is_validated(client: AsyncClient, anna: User) -> None:
    book = await create_gift(client)

    assert (await upload(client, book, label="")).status_code == 422
    assert (await upload(client, book, label="x" * 101)).status_code == 422
    assert (await upload(client, book, label="  Laden  ")).json()["label"] == "Laden"
    no_file = await client.post(IMAGES, data={"gift_id": book, "label": "Laden"})
    assert no_file.status_code == 422
    no_gift = await client.post(
        IMAGES, data={"label": "Laden"}, files={"file": ("foto.jpg", JPEG, "image/jpeg")}
    )
    assert no_gift.status_code == 422


@pytest.mark.requirement("F-07")
async def test_update_changes_only_the_label(client: AsyncClient, anna: User) -> None:
    book = await create_gift(client)
    image = await create_image(client, book, "Alt")

    r = await client.put(f"{IMAGES}/{image['id']}", json={"label": "  Neu  "})

    assert r.status_code == 200
    assert r.json() == {**image, "label": "Neu"}
    assert (await client.put(f"{IMAGES}/{image['id']}", json={"label": ""})).status_code == 422


@pytest.mark.requirement("F-07")
async def test_list_is_oldest_first_and_can_be_narrowed_to_a_gift(
    client: AsyncClient, anna: User
) -> None:
    book = await create_gift(client, "Buch")
    game = await create_gift(client, "Spiel")
    first = await create_image(client, book, "Erstes")
    other = await create_image(client, game, "Spiel")
    second = await create_image(client, book, "Zweites")

    everything = (await client.get(IMAGES)).json()
    assert [i["id"] for i in everything["items"]] == [first["id"], other["id"], second["id"]]
    narrowed = (await client.get(IMAGES, params={"gift_id": book})).json()
    assert [i["id"] for i in narrowed["items"]] == [first["id"], second["id"]]
    assert narrowed["total"] == 2
    page = (await client.get(IMAGES, params={"limit": 1, "offset": 1})).json()
    assert [i["id"] for i in page["items"]] == [other["id"]]
    assert page["total"] == 3


@pytest.mark.requirement("F-07")
async def test_deleted_image_is_gone(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    image = await create_image(client, await create_gift(client))

    assert (await client.delete(f"{IMAGES}/{image['id']}")).status_code == 204
    session.expire_all()

    assert (await client.get(f"{IMAGES}/{image['id']}")).status_code == 404
    assert (await client.get(f"{IMAGES}/{image['id']}/content")).status_code == 404
    assert (await client.delete(f"{IMAGES}/{image['id']}")).status_code == 404


@pytest.mark.requirement("F-07")
async def test_unknown_or_malformed_id(client: AsyncClient, anna: User) -> None:
    assert (await client.get(f"{IMAGES}/{UNKNOWN_ID}")).status_code == 404
    assert (await client.get(f"{IMAGES}/{UNKNOWN_ID}/content")).status_code == 404
    assert (await client.get(f"{IMAGES}/not-a-uuid")).status_code == 422


@pytest.mark.requirement("F-07")
async def test_links_and_images_stay_apart(client: AsyncClient, anna: User) -> None:
    book = await create_gift(client)
    image = await create_image(client, book)
    link = (
        await client.post(LINKS, json={"gift_id": book, "label": "Shop", "url": "https://a.de"})
    ).json()

    assert [i["id"] for i in (await client.get(LINKS)).json()["items"]] == [link["id"]]
    assert [i["id"] for i in (await client.get(IMAGES)).json()["items"]] == [image["id"]]
    assert (await client.get(f"{LINKS}/{image['id']}")).status_code == 404
    assert (await client.get(f"{IMAGES}/{link['id']}")).status_code == 404


@pytest.mark.requirement("F-07", "Q-03")
async def test_images_require_login(client: AsyncClient) -> None:
    item = f"{IMAGES}/{UNKNOWN_ID}"
    assert (await client.get(IMAGES)).status_code == 401
    assert (await upload(client, UNKNOWN_ID)).status_code == 401
    assert (await client.get(item)).status_code == 401
    assert (await client.put(item, json={"label": "Neu"})).status_code == 401
    assert (await client.delete(item)).status_code == 401
    assert (await client.get(f"{item}/content")).status_code == 401


# --- Tenant separation (Q-01) --------------------------------------------------


@pytest.mark.requirement("F-07", "Q-01")
@pytest.mark.parametrize("method", ITEM_METHODS)
async def test_images_of_another_account_are_invisible(
    client: AsyncClient, session: AsyncSession, anna: User, method: str
) -> None:
    image = await create_image(client, await create_gift(client))

    await assert_invisible_to_other_account(
        client,
        session,
        method=method,
        collection=IMAGES,
        item_id=image["id"],
        replacement={"label": "Hacked"},
    )


@pytest.mark.requirement("F-07", "Q-01")
async def test_content_of_another_account_is_invisible(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    image = await create_image(client, await create_gift(client))

    await log_in_new_user(client, session, "peter@example.com")

    r = await client.get(f"{IMAGES}/{image['id']}/content")
    assert r.status_code == 404
    assert r.json()["title"] == "Not Found"


@pytest.mark.requirement("F-07", "Q-01")
async def test_upload_to_a_foreign_gift_is_rejected(
    client: AsyncClient, session: AsyncSession, anna: User, uploads_dir: Path
) -> None:
    foreign = await bobs_gift(session)

    r = await upload(client, str(foreign.id))

    assert r.status_code == 404
    assert stored_files(uploads_dir) == []
    # Same answer as for an idea that does not exist at all.
    unknown = await upload(client, UNKNOWN_ID)
    assert unknown.status_code == 404
    assert r.json() == unknown.json()
    assert r.json()["detail"] == "Gift not found"


@pytest.mark.requirement("F-07", "Q-01")
async def test_list_filtered_to_a_foreign_gift_is_empty(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    foreign = await bobs_gift(session)
    session.add(
        Attachment(
            gift_id=foreign.id, kind=AttachmentKind.IMAGE, label="Bobs Bild", **file_columns(anna)
        )
    )
    await session.flush()

    r = await client.get(IMAGES, params={"gift_id": str(foreign.id)})

    assert r.json() == {"items": [], "total": 0, "limit": 50, "offset": 0}


# --- Files go with their image, idea and account (F-07, F-17) -------------------
# The client fixture never commits, so these tests call the service and commit themselves.


@pytest.mark.requirement("F-07")
async def test_deleting_an_image_removes_its_file_after_commit(
    client: AsyncClient, session: AsyncSession, anna: User, uploads_dir: Path
) -> None:
    image = await create_image(client, await create_gift(client))
    [stored] = stored_files(uploads_dir)

    await image_service.delete_image(session, anna.id, uuid.UUID(image["id"]))
    assert stored.exists()
    await session.commit()

    assert not stored.exists()


@pytest.mark.requirement("F-07")
async def test_deleting_a_gift_removes_its_image_files(
    client: AsyncClient, session: AsyncSession, anna: User, uploads_dir: Path
) -> None:
    book = await create_gift(client, "Buch")
    await create_image(client, book, "Eins")
    await create_image(client, book, "Zwei")
    game = await create_gift(client, "Spiel")
    await create_image(client, game)
    before = stored_files(uploads_dir)

    await gift_service.delete_gift(session, anna.id, uuid.UUID(book))
    await session.commit()

    [kept] = stored_files(uploads_dir)
    assert kept in before
    game_image = await session.scalar(
        select(Attachment).where(Attachment.gift_id == uuid.UUID(game))
    )
    assert game_image is not None
    assert kept == uploads_dir / str(game_image.storage_path)


@pytest.mark.requirement("F-07", "F-17")
async def test_deleting_the_account_removes_all_its_files(
    client: AsyncClient, session: AsyncSession, anna: User, uploads_dir: Path
) -> None:
    book = await create_gift(client)
    await create_image(client, book)
    await create_image(client, book)
    other = uploads_dir / str(uuid.uuid4()) / "bild.webp"
    other.parent.mkdir()
    other.write_bytes(b"webp bytes")

    await auth_service.delete_account(session, anna)
    await session.commit()

    assert not (uploads_dir / str(anna.id)).exists()
    assert other.exists()


@pytest.mark.requirement("F-07")
async def test_deleting_a_gift_over_http_deletes_its_images(
    client: AsyncClient, session: AsyncSession, anna: User
) -> None:
    book = await create_gift(client)
    image = await create_image(client, book)

    assert (await client.delete(f"{GIFTS}/{book}")).status_code == 204
    session.expire_all()

    assert (await client.get(f"{IMAGES}/{image['id']}")).status_code == 404
    assert await session.scalar(select(func.count()).select_from(Attachment)) == 0


# --- Shared view (F-14) --------------------------------------------------------

SHARE_LINK_NOT_FOUND = {
    "type": "about:blank",
    "title": "Not Found",
    "status": 404,
    "detail": "Share link not found",
}


async def create_person(client: AsyncClient, name: str) -> str:
    return (await client.post(PEOPLE, json={"name": name})).json()["id"]


async def create_gift_for(client: AsyncClient, title: str, people: list[str]) -> str:
    return (await client.post(GIFTS, json={"title": title, "person_ids": people})).json()["id"]


async def share(client: AsyncClient, people: list[str], **fields: object) -> dict[str, Any]:
    r = await client.post(SHARE_LINKS, json={"person_ids": people, **fields})
    assert r.status_code == 201
    return r.json()


@pytest.mark.requirement("F-14", "Q-01")
async def test_shared_view_lists_the_images_of_shared_ideas(
    client: AsyncClient, anna: User, clock: FixedClock
) -> None:
    lena = await create_person(client, "Lena")
    tom = await create_person(client, "Tom")
    first = await create_image(client, await create_gift_for(client, "Buch", [lena]), "Laden")
    secret = await create_gift_for(client, "Geheim", [tom])
    await create_image(client, secret, "Nicht teilen")
    created = await share(client, [lena])
    client.cookies.clear()

    shared = (await client.get(f"{SHARED}/{created['token']}")).json()

    [book] = shared["people"][0]["gifts"]
    assert book["images"] == [{"id": first["id"], "label": "Laden"}]
    assert "Nicht teilen" not in str(shared)


@pytest.mark.requirement("F-14", "Q-03")
async def test_shared_image_can_be_fetched_with_the_token(
    client: AsyncClient, anna: User, clock: FixedClock, uploads_dir: Path
) -> None:
    lena = await create_person(client, "Lena")
    image = await create_image(client, await create_gift_for(client, "Buch", [lena]))
    created = await share(client, [lena])
    client.cookies.clear()

    r = await client.get(f"{SHARED}/{created['token']}/images/{image['id']}")

    assert r.status_code == 200
    [stored] = stored_files(uploads_dir)
    assert r.content == stored.read_bytes()
    assert r.headers["content-type"] == "image/webp"
    assert r.headers["cache-control"] == "private, no-store"


@pytest.mark.requirement("F-14")
async def test_shared_image_of_an_idea_for_two_shared_people(
    client: AsyncClient, anna: User, clock: FixedClock
) -> None:
    lena = await create_person(client, "Lena")
    max_ = await create_person(client, "Max")
    image = await create_image(client, await create_gift_for(client, "Spiel", [lena, max_]))
    created = await share(client, [lena, max_])
    client.cookies.clear()

    r = await client.get(f"{SHARED}/{created['token']}/images/{image['id']}")

    assert r.status_code == 200


@pytest.mark.requirement("F-14", "Q-01", "Q-03")
@pytest.mark.parametrize(
    "case",
    ["unknown-token", "expired", "deactivated", "idea-not-shared", "other-account", "link-id"],
)
async def test_shared_image_is_refused(
    client: AsyncClient, session: AsyncSession, anna: User, clock: FixedClock, case: str
) -> None:
    lena = await create_person(client, "Lena")
    tom = await create_person(client, "Tom")
    book = await create_gift_for(client, "Buch", [lena])
    shared_image = await create_image(client, book)
    hidden_image = await create_image(client, await create_gift_for(client, "Geheim", [tom]))
    link = await client.post(LINKS, json={"gift_id": book, "label": "Shop", "url": "https://a.de"})
    created = await share(client, [lena], expires_at="2026-01-02T12:00:00+00:00")
    token, image_id = created["token"], shared_image["id"]

    match case:
        case "unknown-token":
            token = "unbekannt"
        case "expired":
            clock.advance(timedelta(days=2))
        case "deactivated":
            body = {"person_ids": [lena], "active": False}
            assert (
                await client.put(f"{SHARE_LINKS}/{created['id']}", json=body)
            ).status_code == 200
        case "idea-not-shared":
            image_id = hidden_image["id"]
        case "other-account":
            owner = Cookies(client.cookies)
            await log_in_new_user(client, session, "peter@example.com")
            image_id = (await create_image(client, await create_gift(client, "Peters Idee")))["id"]
            client.cookies = owner
        case _:
            image_id = link.json()["id"]
    client.cookies.clear()

    r = await client.get(f"{SHARED}/{token}/images/{image_id}")

    assert r.status_code == 404
    assert r.json() == SHARE_LINK_NOT_FOUND
