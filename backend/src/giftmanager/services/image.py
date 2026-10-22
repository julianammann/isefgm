"""Labelled images on gift ideas (F-07). No HTTP in here.

Images are the rows of `attachment` with kind `image`; links share the table. An attachment
has no owner_id; this module scopes its queries through gift.owner_id. The files lie on the
uploads volume (core/uploads.py) and are re-encoded on the way in (core/imaging.py).
"""

import uuid
from collections.abc import Iterable

from sqlalchemy import Select, func, select
from sqlalchemy.ext.asyncio import AsyncSession

from giftmanager.core import imaging, uploads
from giftmanager.core.errors import ConflictError, NotFoundError
from giftmanager.models import Attachment, AttachmentKind, Gift
from giftmanager.services.ownership import owned, paginate

MAX_IMAGES_PER_GIFT = 5


def _owned_images(owner_id: uuid.UUID) -> Select[tuple[Attachment]]:
    """Select images whose gift idea belongs to the given account; links are left out."""
    return (
        select(Attachment)
        .join(Gift, Gift.id == Attachment.gift_id)
        .where(Gift.owner_id == owner_id, Attachment.kind == AttachmentKind.IMAGE)
    )


async def list_images(
    session: AsyncSession,
    owner_id: uuid.UUID,
    *,
    gift_id: uuid.UUID | None,
    limit: int,
    offset: int,
) -> tuple[list[Attachment], int]:
    """Return one page of the owner's images, oldest first, and the total count.

    With `gift_id`, only the images of that idea; an idea of another account yields an
    empty page.
    """
    statement = _owned_images(owner_id)
    if gift_id is not None:
        statement = statement.where(Attachment.gift_id == gift_id)
    return await paginate(session, statement.order_by(Attachment.id), limit=limit, offset=offset)


async def get_image(session: AsyncSession, owner_id: uuid.UUID, image_id: uuid.UUID) -> Attachment:
    """Return the owner's image.

    Raises:
        NotFoundError: The image does not exist or belongs to another account.
    """
    image = await session.scalar(_owned_images(owner_id).where(Attachment.id == image_id))
    if image is None:
        raise NotFoundError("Image not found")
    return image


async def create_image(
    session: AsyncSession, owner_id: uuid.UUID, *, gift_id: uuid.UUID, label: str, data: bytes
) -> Attachment:
    """Re-encode an upload as WebP, store it and add it to one of the owner's gift ideas.

    Raises:
        ContentTooLargeError: More than 5 MB or more than 24 megapixels.
        UnsupportedMediaTypeError: Not a JPEG, PNG or WebP image.
        ServiceUnavailableError: Too many uploads are being processed.
        NotFoundError: The idea does not exist or belongs to another account.
        ConflictError: The idea already holds 5 images.
    """
    webp = await imaging.convert_to_webp(data)
    # Locked until the commit, so two uploads at once cannot both take the fifth place.
    gift = await session.scalar(owned(Gift, owner_id).where(Gift.id == gift_id).with_for_update())
    if gift is None:
        raise NotFoundError("Gift not found")
    count = await session.scalar(
        select(func.count())
        .select_from(Attachment)
        .where(Attachment.gift_id == gift_id, Attachment.kind == AttachmentKind.IMAGE)
    )
    if (count or 0) >= MAX_IMAGES_PER_GIFT:
        raise ConflictError(f"A gift idea holds at most {MAX_IMAGES_PER_GIFT} images.")

    storage_path = uploads.new_storage_path(owner_id)
    await uploads.write(session, storage_path, webp)
    image = Attachment(
        gift_id=gift_id,
        kind=AttachmentKind.IMAGE,
        label=label,
        storage_path=storage_path,
        mime_type=imaging.MIME_TYPE,
        size_bytes=len(webp),
    )
    session.add(image)
    await session.flush()
    return image


async def update_image(
    session: AsyncSession, owner_id: uuid.UUID, image_id: uuid.UUID, *, label: str
) -> Attachment:
    """Change the label of the owner's image; file and idea stay as they are.

    Raises:
        NotFoundError: The image does not exist or belongs to another account.
    """
    image = await get_image(session, owner_id, image_id)
    image.label = label
    await session.flush()
    return image


async def delete_image(session: AsyncSession, owner_id: uuid.UUID, image_id: uuid.UUID) -> None:
    """Delete the owner's image; its file goes once the deletion has committed."""
    image = await get_image(session, owner_id, image_id)
    _delete_files_after_commit(session, [image])
    await session.delete(image)
    await session.flush()


async def delete_files_of_gift(session: AsyncSession, gift_id: uuid.UUID) -> None:
    """Remove the image files of a gift idea once its deletion has committed."""
    images = await session.scalars(
        select(Attachment).where(
            Attachment.gift_id == gift_id, Attachment.kind == AttachmentKind.IMAGE
        )
    )
    _delete_files_after_commit(session, images)


def _delete_files_after_commit(session: AsyncSession, images: Iterable[Attachment]) -> None:
    for image in images:
        if image.storage_path is not None:  # always set for images (ck_attachment_image_has_file)
            uploads.delete_after_commit(session, image.storage_path)
