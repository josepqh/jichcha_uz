import io

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from PIL import Image
from rest_framework.test import APIClient

from tests.factories import UserFactory


@pytest.fixture(autouse=True)
def _clear_cache():
    """Throttle counters live in the cache; start every test from zero."""
    from django.core.cache import cache

    cache.clear()
    yield
    cache.clear()


@pytest.fixture(autouse=True)
def media_root(settings, tmp_path):
    settings.MEDIA_ROOT = tmp_path / "media"
    return settings.MEDIA_ROOT


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def user(db):
    return UserFactory()


@pytest.fixture
def user_client(user):
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def make_image_bytes(fmt: str = "PNG", size=(64, 48), color=(200, 30, 30, 255), mode="RGBA", **save) -> bytes:
    img = Image.new(mode, size, color if mode != "RGB" else color[:3])
    buf = io.BytesIO()
    img.save(buf, format=fmt, **save)
    return buf.getvalue()


@pytest.fixture
def png_upload():
    def _make(name="photo.png", **kwargs):
        return SimpleUploadedFile(name, make_image_bytes("PNG", **kwargs), content_type="image/png")

    return _make
