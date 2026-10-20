"""Small image files built in memory for upload tests (F-07)."""

from io import BytesIO
from typing import Any

from PIL import Image


def make_image(
    fmt: str, size: tuple[int, int] = (300, 200), mode: str = "RGB", **save: Any
) -> bytes:
    """Encode a plain image of `size` and `mode` as `fmt`; `save` goes to `Image.save`."""
    buffer = BytesIO()
    Image.new(mode, size).save(buffer, fmt, **save)
    return buffer.getvalue()


def open_image(data: bytes) -> Image.Image:
    """Open encoded image bytes, e.g. the result of a conversion or a stored file."""
    return Image.open(BytesIO(data))
