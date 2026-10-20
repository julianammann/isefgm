"""Image endpoints (F-07): upload, list, show, relabel, delete and fetch images on gift ideas."""

import uuid
from typing import Annotated, Any

from fastapi import APIRouter, File, Form, Query, UploadFile, status
from fastapi.responses import FileResponse

from giftmanager.core import imaging, uploads
from giftmanager.core.auth import CurrentUser
from giftmanager.core.db import SessionDep
from giftmanager.models import Attachment
from giftmanager.schemas.common import Label, Page, problem_responses
from giftmanager.schemas.image import ImageLabelIn, ImageListParams, ImageOut
from giftmanager.services import image as image_service

router = APIRouter(prefix="/images", tags=["images"])

_NOT_FOUND_NOTE = " An image of another account returns 404, like a missing one."

# 200 body of the file routes, so OpenAPI and the generated frontend types know it.
IMAGE_FILE_RESPONSE: dict[int | str, dict[str, Any]] = {
    200: {"content": {imaging.MIME_TYPE: {}}, "description": "The image as WebP."}
}


def image_response(image: Attachment) -> FileResponse:
    """Serve the stored file of an image; no browser or shared cache keeps it."""
    assert image.storage_path is not None  # noqa: S101 - ck_attachment_image_has_file
    assert image.mime_type is not None  # noqa: S101 - ck_attachment_image_has_file
    return FileResponse(
        uploads.resolve(image.storage_path),
        media_type=image.mime_type,
        headers={"Cache-Control": "private, no-store"},
    )


@router.get(
    "",
    operation_id="listImages",
    summary="List images",
    description="Returns the images of the current account, oldest first, one page at a time. "
    "`gift_id` narrows the list to one idea; an idea of another account gives an empty page.",
    responses=problem_responses(401),
)
async def list_images(
    user: CurrentUser,
    session: SessionDep,
    page: Annotated[ImageListParams, Query()],
) -> Page[ImageOut]:
    """Return one page of the current account's images."""
    images, total = await image_service.list_images(
        session, user.id, gift_id=page.gift_id, limit=page.limit, offset=page.offset
    )
    return Page[ImageOut](
        items=[ImageOut.model_validate(image) for image in images],
        total=total,
        limit=page.limit,
        offset=page.offset,
    )


@router.post(
    "",
    status_code=status.HTTP_201_CREATED,
    operation_id="createImage",
    summary="Upload image",
    description="Adds a labelled image to a gift idea of the current account. Accepts JPEG, "
    "PNG and WebP up to 5 MB and 24 megapixels, judged by the content, not by the file name "
    "or type (415 for anything else, 413 if larger). The image is turned upright, shrunk to "
    "at most 2000 px on its long side and stored as WebP without EXIF or XMP metadata. An "
    "idea holds at most 5 images (409). While too many uploads are in progress the API "
    "answers 503 with Retry-After. `gift_id` must be a gift idea of the account; an idea of "
    "another account returns 404, like a missing one, and nothing is saved.",
    responses=problem_responses(401, 404, 409, 413, 415, 503),
)
async def create_image(
    gift_id: Annotated[
        uuid.UUID,
        Form(
            description="ID of the account's gift idea the image belongs to.",
            examples=["0199a8c2-5e3b-7f10-8a4d-2c6e9b1f3a70"],
        ),
    ],
    label: Annotated[
        Label, Form(description="Label, 1 to 100 characters.", examples=["Bild vom Laden"])
    ],
    file: Annotated[UploadFile, File(description="JPEG, PNG or WebP, up to 5 MB.")],
    user: CurrentUser,
    session: SessionDep,
) -> ImageOut:
    """Upload an image to a gift idea of the current account."""
    # One byte over the limit is enough to reject the file; the rest is never read.
    data = await file.read(imaging.MAX_UPLOAD_BYTES + 1)
    image = await image_service.create_image(
        session, user.id, gift_id=gift_id, label=label, data=data
    )
    return ImageOut.model_validate(image)


@router.get(
    "/{image_id}",
    operation_id="getImage",
    summary="Show image",
    description="Returns the details of one image of the current account; the file itself "
    "comes from `/images/{image_id}/content`." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def get_image(image_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> ImageOut:
    """Return one image of the current account."""
    image = await image_service.get_image(session, user.id, image_id)
    return ImageOut.model_validate(image)


@router.get(
    "/{image_id}/content",
    operation_id="getImageContent",
    summary="Fetch image file",
    description="Returns the stored WebP file of one image of the current account, marked "
    "`Cache-Control: private, no-store`." + _NOT_FOUND_NOTE,
    response_class=FileResponse,
    responses=IMAGE_FILE_RESPONSE | problem_responses(401, 404),
)
async def get_image_content(
    image_id: uuid.UUID, user: CurrentUser, session: SessionDep
) -> FileResponse:
    """Return the file of one image of the current account."""
    image = await image_service.get_image(session, user.id, image_id)
    return image_response(image)


@router.put(
    "/{image_id}",
    operation_id="updateImage",
    summary="Update image label",
    description="Replaces the label of the image. The file and the gift idea cannot be "
    "changed; upload a new image instead." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def update_image(
    image_id: uuid.UUID, body: ImageLabelIn, user: CurrentUser, session: SessionDep
) -> ImageOut:
    """Change the label of an image of the current account."""
    image = await image_service.update_image(session, user.id, image_id, label=body.label)
    return ImageOut.model_validate(image)


@router.delete(
    "/{image_id}",
    status_code=status.HTTP_204_NO_CONTENT,
    operation_id="deleteImage",
    summary="Delete image",
    description="Deletes the image and its file. Cannot be undone." + _NOT_FOUND_NOTE,
    responses=problem_responses(401, 404),
)
async def delete_image(image_id: uuid.UUID, user: CurrentUser, session: SessionDep) -> None:
    """Delete an image of the current account."""
    await image_service.delete_image(session, user.id, image_id)
