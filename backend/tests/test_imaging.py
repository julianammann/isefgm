"""Re-encoding of uploaded images (F-07, Q-03): format check, limits, WebP without metadata."""

from io import BytesIO
from typing import Any

import pytest
from anyio import CapacityLimiter
from PIL import Image
from PIL.ExifTags import GPS, IFD, Base

from giftmanager.core import imaging
from giftmanager.core.errors import (
    ContentTooLargeError,
    ServiceUnavailableError,
    UnsupportedMediaTypeError,
)
from tests.images import make_image, open_image


def noisy_jpeg(size: tuple[int, int] = (300, 200)) -> bytes:
    """A JPEG with real content, so cutting it in half leaves a truncated image."""
    buffer = BytesIO()
    Image.effect_noise(size, 64).convert("RGB").save(buffer, "JPEG")
    return buffer.getvalue()


@pytest.mark.requirement("F-07")
@pytest.mark.parametrize("fmt", ["JPEG", "PNG", "WEBP"])
def test_jpeg_png_and_webp_become_webp(fmt: str) -> None:
    out = open_image(imaging.to_webp(make_image(fmt)))

    assert out.format == "WEBP"
    assert out.size == (300, 200)


@pytest.mark.requirement("F-07")
def test_mpo_phone_photo_is_accepted() -> None:
    buffer = BytesIO()
    first, second = Image.new("RGB", (300, 200)), Image.new("RGB", (300, 200))
    first.save(buffer, "MPO", save_all=True, append_images=[second])
    assert open_image(buffer.getvalue()).format == "MPO"

    assert open_image(imaging.to_webp(buffer.getvalue())).format == "WEBP"


@pytest.mark.requirement("F-07")
@pytest.mark.parametrize(
    ("size", "expected"),
    [((3000, 1500), (2000, 1000)), ((1500, 3000), (1000, 2000)), ((2000, 2000), (2000, 2000))],
)
def test_long_side_is_scaled_to_2000_px(size: tuple[int, int], expected: tuple[int, int]) -> None:
    assert open_image(imaging.to_webp(make_image("PNG", size))).size == expected


@pytest.mark.requirement("F-07")
def test_small_image_is_not_enlarged() -> None:
    assert open_image(imaging.to_webp(make_image("JPEG", (800, 600)))).size == (800, 600)


@pytest.mark.requirement("F-07", "Q-03")
def test_exif_and_location_are_removed() -> None:
    exif = Image.Exif()
    exif[Base.Make] = "TestCam"
    exif[Base.GPSInfo] = {GPS.GPSLatitudeRef: "N", GPS.GPSLatitude: (52.0, 31.0, 0.0)}
    source = make_image("JPEG", exif=exif)
    assert open_image(source).getexif().get_ifd(IFD.GPSInfo)

    out = open_image(imaging.to_webp(source))

    assert dict(out.getexif()) == {}
    assert "exif" not in out.info
    assert "xmp" not in out.info


@pytest.mark.requirement("F-07")
def test_orientation_is_applied_before_exif_is_dropped() -> None:
    exif = Image.Exif()
    exif[Base.Orientation] = 6  # rotate 90 degrees clockwise to display

    out = open_image(imaging.to_webp(make_image("JPEG", (300, 100), exif=exif)))

    assert out.size == (100, 300)


@pytest.mark.requirement("F-07")
@pytest.mark.parametrize(
    ("fmt", "mode", "expected"), [("PNG", "RGBA", "RGBA"), ("JPEG", "RGB", "RGB")]
)
def test_transparency_is_kept(fmt: str, mode: str, expected: str) -> None:
    assert open_image(imaging.to_webp(make_image(fmt, mode=mode))).mode == expected


@pytest.mark.requirement("F-07")
def test_animation_keeps_only_the_first_frame() -> None:
    buffer = BytesIO()
    red, blue = Image.new("RGB", (50, 50), "red"), Image.new("RGB", (50, 50), "blue")
    red.save(buffer, "WEBP", save_all=True, append_images=[blue])
    assert getattr(open_image(buffer.getvalue()), "n_frames", 1) == 2

    out = open_image(imaging.to_webp(buffer.getvalue()))

    assert getattr(out, "n_frames", 1) == 1
    r, g, b = out.convert("RGB").crop((25, 25, 26, 26)).tobytes()
    assert r > 200
    assert g < 50
    assert b < 50


@pytest.mark.requirement("F-07")
@pytest.mark.parametrize(
    ("fmt", "mode", "save", "expected"),
    [
        ("JPEG", "CMYK", {}, "RGB"),
        ("PNG", "P", {"transparency": 0}, "RGBA"),
        ("PNG", "LA", {}, "RGBA"),
        ("PNG", "I;16", {}, "RGB"),
        ("JPEG", "L", {}, "RGB"),
    ],
)
def test_unusual_colour_modes_are_converted(
    fmt: str, mode: str, save: dict[str, Any], expected: str
) -> None:
    assert open_image(imaging.to_webp(make_image(fmt, mode=mode, **save))).mode == expected


@pytest.mark.requirement("F-07")
def test_icc_profile_is_kept() -> None:
    # Pillow embeds and reads the profile as opaque bytes; a real one is not needed.
    profile = b"colour profile of the camera"

    out = open_image(imaging.to_webp(make_image("JPEG", icc_profile=profile)))

    assert out.info["icc_profile"] == profile


@pytest.mark.requirement("F-07", "Q-03")
@pytest.mark.parametrize(
    "data",
    [
        pytest.param(make_image("GIF"), id="gif"),
        pytest.param(make_image("BMP"), id="bmp"),
        pytest.param(make_image("TIFF"), id="tiff"),
        pytest.param(b'<svg xmlns="http://www.w3.org/2000/svg" width="10" height="10"/>', id="svg"),
        pytest.param(b"%PDF-1.4\n1 0 obj\n<<>>\nendobj\n", id="pdf"),
        pytest.param(b"hello", id="text"),
        pytest.param(b"", id="empty"),
        pytest.param(noisy_jpeg()[: len(noisy_jpeg()) // 2], id="truncated-jpeg"),
    ],
)
def test_not_an_allowed_image_is_rejected(data: bytes) -> None:
    with pytest.raises(UnsupportedMediaTypeError):
        imaging.to_webp(data)


@pytest.mark.requirement("F-07", "Q-03")
def test_more_than_5_mb_is_rejected() -> None:
    with pytest.raises(ContentTooLargeError):
        imaging.to_webp(b"\xff" * (5 * 1024 * 1024 + 1))
    # Exactly 5 MB passes the size check and fails only as a non-image.
    with pytest.raises(UnsupportedMediaTypeError):
        imaging.to_webp(b"\xff" * (5 * 1024 * 1024))


@pytest.mark.requirement("F-07", "Q-03")
def test_more_than_24_megapixels_is_rejected() -> None:
    with pytest.raises(ContentTooLargeError):
        imaging.to_webp(make_image("PNG", (5000, 5000), mode="L"))

    out = open_image(imaging.to_webp(make_image("JPEG", (6000, 4000), mode="L")))
    assert out.size == (2000, 1333)


@pytest.mark.requirement("F-07")
async def test_full_queue_returns_503(monkeypatch: pytest.MonkeyPatch) -> None:
    full = CapacityLimiter(1)
    full.acquire_on_behalf_of_nowait("flood")
    monkeypatch.setattr(imaging, "_admission_limiter", full)

    with pytest.raises(ServiceUnavailableError) as busy:
        await imaging.convert_to_webp(make_image("PNG"))
    assert busy.value.detail == "Too many image uploads at once; try again in a few seconds"

    full.release_on_behalf_of("flood")
    assert open_image(await imaging.convert_to_webp(make_image("PNG"))).format == "WEBP"
