"""Re-encoding of uploaded images (F-07, Q-03): checked by content, stored as WebP only."""

from io import BytesIO
from typing import Final

from anyio import CapacityLimiter, WouldBlock, to_thread
from PIL import Image, ImageOps

from giftmanager.core.errors import (
    ContentTooLargeError,
    ServiceUnavailableError,
    UnsupportedMediaTypeError,
)

MAX_UPLOAD_BYTES: Final = 5 * 1024 * 1024
# Checked from the header before decoding: a small file can unpack to a huge bitmap.
MAX_PIXELS: Final = 24_000_000
MAX_SIDE: Final = 2000
WEBP_QUALITY: Final = 85
MIME_TYPE: Final = "image/webp"

# The Pillow plugins tried on an upload. MPO, the multi-picture JPEG of many phones,
# comes in through the JPEG opener.
_FORMATS: Final = ("JPEG", "PNG", "WEBP")

# A 24 MP image takes about 100 MiB once decoded, and the api container has 512 MiB of
# which Argon2 may hold 192 MiB (core/security.py). So one image at a time.
_processing_limiter = CapacityLimiter(1)

# A waiting upload holds the request's pooled DB connection (CurrentUser already queried),
# so the wait is bounded: 1 processing + 2 waiting. With the 11 admitted logins that is 14
# of the pool's 15 connections; the next upload is turned away at once.
_admission_limiter = CapacityLimiter(1 + 2)


def to_webp(data: bytes) -> bytes:
    """Return the upload as WebP: upright, at most 2000 px on the long side, no metadata.

    The ICC colour profile is kept; EXIF and XMP are dropped. Transparency is kept.

    Raises:
        ContentTooLargeError: More than 5 MB or more than 24 megapixels.
        UnsupportedMediaTypeError: Not a JPEG, PNG or WebP image, or a broken one.
    """
    if len(data) > MAX_UPLOAD_BYTES:
        raise ContentTooLargeError("Images may be at most 5 MB")
    try:
        image = Image.open(BytesIO(data), formats=_FORMATS)
        if image.width * image.height > MAX_PIXELS:
            raise ContentTooLargeError("Images may have at most 24 megapixels")
        icc_profile = image.info.get("icc_profile")
        image.draft("RGB", (MAX_SIDE, MAX_SIDE))  # JPEG only: decode at a reduced scale
        image.load()
    except (OSError, SyntaxError, ValueError) as exc:
        raise UnsupportedMediaTypeError("File is not a JPEG, PNG or WebP image") from exc

    image = image.convert("RGBA" if image.has_transparency_data else "RGB")
    image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    # Shrunk first, so turning it upright copies the small image, not the full one.
    image = ImageOps.exif_transpose(image)

    out = BytesIO()
    image.save(out, "WEBP", quality=WEBP_QUALITY, icc_profile=icc_profile)
    return out.getvalue()


async def convert_to_webp(data: bytes) -> bytes:
    """Run `to_webp` in a worker thread, one image at a time.

    Raises:
        ServiceUnavailableError: One upload is being processed and two are waiting.
        ContentTooLargeError: See `to_webp`.
        UnsupportedMediaTypeError: See `to_webp`.
    """
    try:
        _admission_limiter.acquire_nowait()
    except WouldBlock:
        raise ServiceUnavailableError(
            "Too many image uploads at once; try again in a few seconds"
        ) from None
    try:
        return await to_thread.run_sync(to_webp, data, limiter=_processing_limiter)
    finally:
        _admission_limiter.release()
