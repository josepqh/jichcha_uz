import pytest
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

TUNNEL = "universe-demo.ngrok-free.app"


@pytest.fixture
def edge(settings):
    settings.EDGE_HOST, settings.EDGE_SECRET = TUNNEL, "s" * 40
    settings.ALLOWED_HOSTS = [TUNNEL, "testserver"]


def test_tunnel_host_needs_the_edge_secret(edge):
    client = APIClient()
    resp = client.get("/api/v1/tools/", HTTP_HOST=TUNNEL)
    assert resp.status_code == 403
    assert client.get("/api/v1/tools/", HTTP_HOST=TUNNEL, HTTP_X_UNIVERSE_EDGE="wrong").status_code == 403
    assert client.get("/api/v1/tools/", HTTP_HOST=TUNNEL, HTTP_X_UNIVERSE_EDGE="s" * 40).status_code == 200


def test_other_hosts_are_untouched(edge):
    assert APIClient().get("/api/v1/tools/").status_code == 200


def test_off_without_settings():
    assert APIClient().get("/api/v1/tools/").status_code == 200
