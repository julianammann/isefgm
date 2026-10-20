"""Labelled images on gift ideas (F-07): upload, delivery and foreign access (Q-01, Q-03)."""

from typing import Any

import pytest
from httpx import AsyncClient
from sqlalchemy.exc import IntegrityError
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.models import Attachment, AttachmentKind, Gift, User
from tests.accounts import log_in_new_user


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
