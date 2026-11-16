import io

import pikepdf
import pillow_heif
import pytest
from PIL import Image

from apps.conversions.formats import detect_image
from apps.conversions.processors import images
from apps.conversions.processors.base import InputFile, ProcessingError, safe_name
from tests.conftest import make_image_bytes

pillow_heif.register_heif_opener()


def write(tmp_path, name, data: bytes, fmt: str) -> InputFile:
    path = tmp_path / f"src-{name}"
    path.write_bytes(data)
    return InputFile(path=path, name=name, fmt=fmt)


def jpeg_with_gps() -> bytes:
    img = Image.new("RGB", (400, 300), (10, 120, 200))
    exif = Image.Exif()
    exif[0x0112] = 6  # orientation: rotate 90 CW
    exif[0x8825] = {1: "N", 2: (41.0, 18.0, 0.0)}  # GPS IFD
    buf = io.BytesIO()
    img.save(buf, format="JPEG", quality=95, exif=exif)
    return buf.getvalue()


class TestDetect:
    def test_detects_by_content_not_extension(self):
        detected = detect_image(io.BytesIO(make_image_bytes("PNG")))
        assert detected is not None and detected.fmt == "png"

    def test_text_is_not_an_image(self):
        assert detect_image(io.BytesIO(b"<svg onload=alert(1)>")) is None

    def test_heic_is_detected(self):
        buf = io.BytesIO()
        Image.new("RGB", (32, 32), "red").save(buf, format="HEIF")
        detected = detect_image(io.BytesIO(buf.getvalue()))
        assert detected is not None and detected.fmt == "heic"


class TestConvert:
    def test_png_with_alpha_to_jpg_is_flattened(self, tmp_path):
        src = write(tmp_path, "logo.png", make_image_bytes("PNG", color=(0, 0, 0, 0)), "png")
        [out] = images.convert_images([src], {"target": "jpg"}, tmp_path)
        assert out.name == "logo.jpg"
        assert out.mime == "image/jpeg"
        with Image.open(out.path) as img:
            assert img.format == "JPEG"
            assert img.getpixel((0, 0)) == (255, 255, 255)

    @pytest.mark.parametrize("target", ["png", "webp", "avif", "gif", "bmp", "tiff"])
    def test_every_output_format_opens(self, tmp_path, target):
        src = write(tmp_path, "a.png", make_image_bytes("PNG"), "png")
        [out] = images.convert_images([src], {"target": target}, tmp_path)
        with Image.open(out.path) as img:
            assert img.size == (64, 48)

    def test_exif_orientation_applied_and_metadata_removed(self, tmp_path):
        src = write(tmp_path, "phone.jpg", jpeg_with_gps(), "jpg")
        [out] = images.convert_images([src], {"target": "png"}, tmp_path)
        with Image.open(out.path) as img:
            assert img.size == (300, 400)  # rotated
            assert not img.getexif()

    def test_corrupt_file_raises_user_error(self, tmp_path):
        src = write(tmp_path, "broken.png", make_image_bytes("PNG")[:60], "png")
        with pytest.raises(ProcessingError) as exc:
            images.convert_images([src], {"target": "jpg"}, tmp_path)
        assert exc.value.code == "corrupt_file"

    def test_decompression_bomb_rejected(self, tmp_path, settings):
        settings.IMAGE_MAX_PIXELS = 1000
        src = write(tmp_path, "big.png", make_image_bytes("PNG", size=(100, 100)), "png")
        with pytest.raises(ProcessingError) as exc:
            images.convert_images([src], {"target": "jpg"}, tmp_path)
        assert exc.value.code == "image_too_large"


class TestCompress:
    def test_jpeg_gets_smaller_and_loses_gps(self, tmp_path):
        noisy = Image.effect_noise((800, 600), 64).convert("RGB")
        buf = io.BytesIO()
        exif = Image.Exif()
        exif[0x8825] = {1: "N", 2: (41.0, 18.0, 0.0)}
        noisy.save(buf, format="JPEG", quality=98, exif=exif)
        src = write(tmp_path, "photo.jpg", buf.getvalue(), "jpg")

        [out] = images.compress_images([src], {"level": "medium"}, tmp_path)

        assert out.path.stat().st_size < src.path.stat().st_size
        with Image.open(out.path) as img:
            assert img.format == "JPEG"
            assert 0x8825 not in img.getexif()

    def test_heic_compresses_to_jpg(self, tmp_path):
        buf = io.BytesIO()
        Image.new("RGB", (64, 64), "blue").save(buf, format="HEIF")
        src = write(tmp_path, "IMG_0001.heic", buf.getvalue(), "heic")
        [out] = images.compress_images([src], {"level": "strong"}, tmp_path)
        assert out.name == "IMG_0001.jpg"

    def test_png_strong_uses_palette(self, tmp_path):
        noisy = Image.effect_noise((300, 300), 80).convert("RGB")
        buf = io.BytesIO()
        noisy.save(buf, format="PNG")
        src = write(tmp_path, "shot.png", buf.getvalue(), "png")
        [out] = images.compress_images([src], {"level": "strong"}, tmp_path)
        assert out.path.stat().st_size < src.path.stat().st_size


class TestImagesToPdf:
    def test_pages_in_given_order_on_a4(self, tmp_path):
        a = write(tmp_path, "first.png", make_image_bytes("PNG", size=(100, 200)), "png")
        b = write(tmp_path, "second.jpg", make_image_bytes("JPEG", mode="RGB", size=(300, 100)), "jpg")
        [out] = images.images_to_pdf([a, b], {"page_size": "a4", "orientation": "auto", "margin": "small"}, tmp_path)

        assert out.name == "first.pdf"
        with pikepdf.open(out.path) as pdf:
            assert len(pdf.pages) == 2
            w0, h0 = (float(v) for v in pdf.pages[0].mediabox[2:])
            w1, h1 = (float(v) for v in pdf.pages[1].mediabox[2:])
        assert h0 > w0  # portrait image -> portrait A4
        assert w1 > h1  # landscape image -> auto-rotated A4
        assert round(min(w0, h0)) == 595  # A4 short side in points

    def test_fit_page_size_matches_image(self, tmp_path):
        a = write(tmp_path, "a.png", make_image_bytes("PNG", size=(120, 80)), "png")
        [out] = images.images_to_pdf([a], {"page_size": "fit", "orientation": "auto", "margin": "none"}, tmp_path)
        with pikepdf.open(out.path) as pdf:
            w, h = (float(v) for v in pdf.pages[0].mediabox[2:])
        assert w > h


@pytest.mark.parametrize(
    ("raw", "expected"),
    [
        ("../../etc/passwd", "passwd"),
        ("C:\\Users\\a\\rasm.png", "rasm.png"),
        ("o'zbek\x00name.jpg", "o'zbek_name.jpg"),
        ("Сурат 1.HEIC", "Сурат 1.HEIC"),
        ("...", "file"),
        ("a" * 300 + ".png", "a" * 116 + ".png"),
    ],
)
def test_safe_name(raw, expected):
    assert safe_name(raw) == expected
