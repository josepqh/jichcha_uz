import pytest
from rest_framework.test import APIClient

from tests.conftest import make_image_bytes

pytestmark = pytest.mark.django_db


def create_task(client, **extra):
    from django.core.files.uploadedfile import SimpleUploadedFile

    files = [SimpleUploadedFile("a.png", make_image_bytes())]
    payload = {"tool": "image-convert", "options": '{"target": "jpg"}', "files": files}
    return client.post("/api/v1/tasks/", payload, **extra)


@pytest.fixture
def secure_cookies(settings):
    settings.GUEST_COOKIE_SECURE = True
    settings.AUTH_COOKIE_SECURE = True
    settings.ALLOWED_HOSTS = ["localhost", "127.0.0.1", "jichcha.uz", "testserver"]


@pytest.mark.parametrize("host", ["localhost:8080", "127.0.0.1:8080"])
def test_plain_http_on_localhost_drops_secure_so_safari_keeps_the_cookie(secure_cookies, host):
    resp = create_task(APIClient(), HTTP_HOST=host)
    assert resp.status_code == 202
    assert resp.cookies["jichcha_guest"]["secure"] == ""


def test_real_hosts_and_https_keep_secure(secure_cookies):
    assert create_task(APIClient(), HTTP_HOST="jichcha.uz").cookies["jichcha_guest"]["secure"] is True
    assert create_task(APIClient(), HTTP_HOST="localhost", secure=True).cookies["jichcha_guest"]["secure"] is True


def test_refresh_cookie_too(secure_cookies):
    resp = APIClient().post(
        "/api/v1/auth/register/",
        {"email": "safari@example.com", "password": "Str0ng-pass-123"},
        format="json",
        HTTP_HOST="localhost:8080",
    )
    assert resp.cookies["jichcha_refresh"]["secure"] == ""
