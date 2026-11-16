from unittest import mock

import pytest
import requests

from apps.users import turnstile

pytestmark = pytest.mark.django_db
REGISTER = "/api/v1/auth/register/"
RESET = "/api/v1/auth/password/reset/"
BODY = {"email": "ali@example.uz", "password": "Str0ng-pass-123"}


@pytest.fixture
def on(settings):
    settings.TURNSTILE_SECRET_KEY = "secret"


def cloudflare(success=True, error=None):
    response = mock.Mock(ok=True, json=mock.Mock(return_value={"success": success}))
    return mock.patch.object(turnstile.requests, "post", return_value=response, side_effect=error)


def test_off_by_default(api_client):
    assert api_client.post(REGISTER, BODY, format="json").status_code == 201


def test_missing_token_is_refused(api_client, on):
    resp = api_client.post(REGISTER, BODY, format="json")
    assert (resp.status_code, resp.data["error"]["code"]) == (400, "captcha_required")


def test_valid_token_passes_and_ip_is_sent(api_client, on):
    with cloudflare(True) as post:
        assert api_client.post(REGISTER, {**BODY, "captcha": "tok"}, format="json").status_code == 201
    assert post.call_args.kwargs["data"] == {"secret": "secret", "response": "tok", "remoteip": "127.0.0.1"}


@pytest.mark.parametrize("kwargs", [{"success": False}, {"error": requests.ConnectionError()}])
def test_rejected_or_unreachable_fails_closed(api_client, on, kwargs):
    with cloudflare(**kwargs):
        resp = api_client.post(REGISTER, {**BODY, "captcha": "tok"}, format="json")
    assert resp.data["error"]["code"] == "captcha_failed"


def test_password_reset_is_covered_too(api_client, on):
    assert api_client.post(RESET, {"email": "x@example.uz"}, format="json").status_code == 400
    with cloudflare(True):
        assert api_client.post(RESET, {"email": "x@example.uz", "captcha": "t"}, format="json").status_code == 202
