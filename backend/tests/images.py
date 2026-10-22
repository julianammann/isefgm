"""Small image files built in memory for upload tests (F-07)."""

import struct
import zlib
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


def png_header_only(width: int, height: int) -> bytes:
    """A PNG that only declares its size: signature, IHDR and IEND, no pixel data."""

    def chunk(kind: bytes, data: bytes) -> bytes:
        crc = zlib.crc32(kind + data)
        return struct.pack(">I", len(data)) + kind + data + struct.pack(">I", crc)

    ihdr = struct.pack(">IIBBBBB", width, height, 8, 0, 0, 0, 0)
    return b"\x89PNG\r\n\x1a\n" + chunk(b"IHDR", ihdr) + chunk(b"IEND", b"")
