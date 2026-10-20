"""Re-encoding of uploaded images (F-07, Q-03): checked by content, stored as WebP only."""

import contextlib
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
MAX_SIDE: Final = 2000
WEBP_QUALITY: Final = 85
MIME_TYPE: Final = "image/webp"

# The Pillow plugins tried on an upload. MPO, the multi-picture JPEG of many phones,
# comes in through the JPEG opener.
_FORMATS: Final = ("JPEG", "PNG", "WEBP")

# Checked from the header before decoding: a small file can unpack to a huge bitmap.
# Measured peak of to_webp at these limits (python:3.14-slim, Pillow 13): JPEG +50 MiB
# (decoded at a reduced scale), PNG up to +170 MiB, WebP up to +190 MiB (Pillow's decoder
# holds two full canvases). With the app and three Argon2 hashes (192 MiB, core/security.py)
# that stays inside the api container's 512 MiB, but only for one image at a time.
MAX_PIXELS: Final = {"JPEG": 24_000_000, "MPO": 24_000_000, "PNG": 16_000_000, "WEBP": 10_000_000}

_processing_limiter = CapacityLimiter(1)

# A waiting upload holds the request's pooled DB connection (CurrentUser already queried),
# so the wait is bounded: 1 processing + 2 waiting. With the 11 admitted logins that is 14
# of the pool's 15 connections; the next upload is turned away at once.
_admission_limiter = CapacityLimiter(1 + 2)


def to_webp(data: bytes) -> bytes:
    """Return the upload as WebP: upright, at most 2000 px on the long side, no metadata.

    The ICC colour profile is kept; EXIF and XMP are dropped. Transparency is kept.

    Raises:
        ContentTooLargeError: More than 5 MB, or more pixels than `MAX_PIXELS` allows for
            the format.
        UnsupportedMediaTypeError: Not a JPEG, PNG or WebP image, or a broken one.
    """
    if len(data) > MAX_UPLOAD_BYTES:
        raise ContentTooLargeError("Images may be at most 5 MB")
    try:
        image = Image.open(BytesIO(data), formats=_FORMATS)
        limit = MAX_PIXELS[str(image.format)]
        if image.width * image.height > limit:
            raise ContentTooLargeError(
                f"{image.format} images may have at most {limit / 1_000_000:g} megapixels"
            )
        icc_profile = image.info.get("icc_profile")
        image.draft("RGB", (MAX_SIDE, MAX_SIDE))  # JPEG only: decode at a reduced scale
        image.load()
    except Image.DecompressionBombError as exc:
        # Pillow's own limit, far above ours, hit while reading the header.
        raise ContentTooLargeError("Image has too many pixels") from exc
    except (OSError, SyntaxError, ValueError) as exc:
        raise UnsupportedMediaTypeError("File is not a JPEG, PNG or WebP image") from exc

    if image.mode.startswith("I"):
        # 16-bit greyscale: converting straight to RGB would clip every tone to white.
        image = Image.eval(image.convert("I"), lambda v: v / 256).convert("L")
    mode = "RGBA" if image.has_transparency_data else "RGB"
    if image.mode != mode:  # a same-mode convert would copy the full bitmap for nothing
        image = image.convert(mode)
    image.thumbnail((MAX_SIDE, MAX_SIDE), Image.Resampling.LANCZOS)
    # Shrunk first, so turning it upright copies the small image, not the full one. A
    # broken EXIF block only loses the orientation, as in a browser.
    with contextlib.suppress(OSError, SyntaxError, ValueError):
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
