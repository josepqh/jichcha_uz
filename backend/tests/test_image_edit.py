import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image

from apps.conversions.processors import images
from apps.conversions.processors.base import InputFile, ProcessingError
from tests.conftest import make_image_bytes


def quadrants(size=(200, 100)) -> Image.Image:
    """Red top-left, green top-right, blue bottom-left, white bottom-right: shows every transform."""
    w, h = size
    img = Image.new("RGB", size)
    for box, colour in (
        ((0, 0, w // 2, h // 2), (255, 0, 0)),
        ((w // 2, 0, w, h // 2), (0, 255, 0)),
        ((0, h // 2, w // 2, h), (0, 0, 255)),
        ((w // 2, h // 2, w, h), (255, 255, 255)),
    ):
        img.paste(colour, box)
    return img


def corner(img: Image.Image, where: str) -> tuple:
    w, h = img.size
    x = 2 if "left" in where else w - 3
    y = 2 if "top" in where else h - 3
    return img.convert("RGB").getpixel((x, y))


RED, GREEN, BLUE = (255, 0, 0), (0, 255, 0), (0, 0, 255)


def test_fractional_crop():
    out = images.edit_image(quadrants(), {"crop": {"x": 0.5, "y": 0, "w": 0.5, "h": 0.5}})
    assert out.size == (100, 50)
    assert corner(out, "top-left") == GREEN


@pytest.mark.parametrize(("aspect", "size"), [("1:1", (100, 100)), ("16:9", (178, 100)), ("3:4", (75, 100))])
def test_centred_aspect_crop(aspect, size):
    assert images.edit_image(quadrants(), {"aspect": aspect}).size == size


def test_rotate_is_clockwise():
    out = images.edit_image(quadrants(), {"rotate": 90})
    assert out.size == (100, 200)
    assert corner(out, "top-right") == RED  # top-left moves to the top-right
    assert corner(out, "top-left") == BLUE


@pytest.mark.parametrize(("flip", "top_left"), [("horizontal", GREEN), ("vertical", BLUE)])
def test_flip(flip, top_left):
    assert corner(images.edit_image(quadrants(), {"flip": flip}), "top-left") == top_left


def test_resize_percent_and_pixels_keep_the_ratio():
    assert images.edit_image(quadrants(), {"resize": "percent", "percent": 50}).size == (100, 50)
    assert images.edit_image(quadrants(), {"resize": "pixels", "width": 60}).size == (60, 30)
    assert images.edit_image(quadrants(), {"resize": "pixels", "height": 30}).size == (60, 30)
    assert images.edit_image(quadrants(), {"resize": "pixels", "width": 40, "height": 40}).size == (40, 40)


def test_order_is_crop_then_rotate_then_resize():
    out = images.edit_image(quadrants(), {"aspect": "1:1", "rotate": 270, "resize": "pixels", "width": 10})
    assert out.size == (10, 10)


def test_refuses_huge_results(settings):
    settings.IMAGE_MAX_PIXELS = 100_000
    with pytest.raises(ProcessingError) as exc:
        images.edit_image(quadrants(), {"resize": "percent", "percent": 400})
    assert exc.value.code == "image_too_large"


def test_keep_format_and_names(tmp_path):
    src = tmp_path / "in.png"
    Image.new("RGBA", (40, 20), (0, 0, 0, 0)).save(src)
    [out] = images.edit_images([InputFile(src, "logo.png", "png")], {"rotate": 90}, tmp_path)
    assert out.name == "logo-edited.png"
    with Image.open(out.path) as img:
        assert img.size == (20, 40) and img.mode == "RGBA"
    [jpg] = images.edit_images([InputFile(src, "logo.png", "png")], {"format": "jpg"}, tmp_path)
    assert jpg.name == "logo-edited.jpg" and jpg.mime == "image/jpeg"


@pytest.mark.django_db
class TestApi:
    def post(self, client, options):
        files = [SimpleUploadedFile("a.png", make_image_bytes())]
        return client.post("/api/v1/tasks/", {"tool": "image-edit", "options": json.dumps(options), "files": files})

    def test_valid(self, api_client):
        assert (
            self.post(api_client, {"rotate": 90, "crop": {"x": 0.1, "y": 0.1, "w": 0.5, "h": 0.5}}).status_code == 202
        )

    @pytest.mark.parametrize(
        "options",
        [
            {"crop": {"x": 0.8, "y": 0, "w": 0.5, "h": 0.5}},  # past the right edge
            {"crop": {"x": 0, "y": 0, "w": 0, "h": 0.5}},
            {"rotate": 45},
            {"resize": "pixels"},  # no width or height
            {"resize": "percent", "percent": 1000},
            {"format": "heic"},
        ],
    )
    def test_invalid(self, api_client, options):
        resp = self.post(api_client, options)
        assert resp.status_code == 400
