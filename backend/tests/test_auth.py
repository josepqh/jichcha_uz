import re
import time
from pathlib import Path
from unittest import mock

import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.conversions.models import Task, UsageCounter
from apps.users.google import GoogleIdentity, GoogleTokenError
from apps.users.models import User
from apps.users.throttles import AuthRateThrottle
from apps.users.tokens import issue_tokens
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"
COOKIE = "uv_refresh"


def register(client, email="ali@example.com", password=PASSWORD, **extra):
    return client.post("/api/v1/auth/register/", {"email": email, "password": password, **extra}, format="json")


def login(client, email="ali@example.com", password=PASSWORD):
    return client.post("/api/v1/auth/login/", {"email": email, "password": password}, format="json")


def bearer(access: str) -> APIClient:
    client = APIClient()
    client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")
    return client


class TestRegisterAndLogin:
    def test_register_logs_in_with_httponly_strict_cookie(self, api_client):
        resp = register(api_client, email="Ali@Example.COM", language="ru")

        assert resp.status_code == 201
        assert resp.data["user"]["email"] == "ali@example.com"
        assert resp.data["user"]["language"] == "ru"
        assert resp.data["user"]["email_verified"] is False
        assert resp.data["access"]
        cookie = resp.cookies[COOKIE]
        assert cookie["httponly"] and cookie["samesite"] == "Strict"
        assert cookie["path"] == "/api/v1/auth/"
        assert "refresh" not in resp.data  # refresh token never reaches JavaScript

    def test_duplicate_email_is_case_insensitive(self, api_client):
        register(api_client)
        resp = register(APIClient(), email="ALI@example.com")
        assert resp.status_code == 409
        assert resp.data["error"]["code"] == "email_taken"

    def test_concurrent_duplicate_signup_returns_409_not_500(self, api_client):
        from django.db import IntegrityError

        with mock.patch.object(User.objects, "create_user", side_effect=IntegrityError("users_email_key")):
            resp = register(api_client)
        assert resp.status_code == 409
        assert resp.data["error"]["code"] == "email_taken"

    def test_weak_password_reports_reasons(self, api_client):
        resp = register(api_client, password="12345678")
        assert resp.status_code == 400
        assert resp.data["error"]["code"] == "weak_password"
        assert "password_too_common" in resp.data["error"]["details"]["reasons"]
        assert not User.objects.exists()

    def test_login_success(self, api_client):
        register(api_client)
        resp = login(APIClient(), email=" ALI@example.com ")
        assert resp.status_code == 200
        assert resp.data["user"]["email"] == "ali@example.com"

    @pytest.mark.parametrize(
        ("email", "password"), [("ali@example.com", "wrong-pass-1"), ("nobody@example.com", PASSWORD)]
    )
    def test_login_failure_is_generic(self, api_client, email, password):
        register(api_client)
        resp = login(APIClient(), email=email, password=password)
        assert resp.status_code == 401
        assert resp.data["error"]["code"] == "invalid_credentials"

    def test_inactive_user_cannot_login(self, api_client):
        UserFactory(email="off@example.com", is_active=False)
        assert login(api_client, email="off@example.com").status_code == 401


class TestSessions:
    def test_refresh_rotates_and_old_token_is_dead(self):
        client = APIClient()
        register(client)
        old = client.cookies[COOKIE].value

        resp = client.post("/api/v1/auth/refresh/")
        assert resp.status_code == 200
        assert resp.data["access"]
        assert resp.data["user"]["email"] == "ali@example.com"
        assert client.cookies[COOKIE].value != old

        replay = APIClient()
        replay.cookies[COOKIE] = old
        resp = replay.post("/api/v1/auth/refresh/")
        assert resp.status_code == 401
        assert resp.data["error"]["code"] == "session_expired"
        assert resp.cookies[COOKIE].value == ""  # cookie cleared

    def test_refresh_without_cookie(self, api_client):
        resp = api_client.post("/api/v1/auth/refresh/")
        assert resp.status_code == 401
        assert resp.data["error"]["code"] == "session_expired"

    def test_logout_revokes_refresh_token(self):
        client = APIClient()
        register(client)
        token = client.cookies[COOKIE].value
        assert client.post("/api/v1/auth/logout/").status_code == 204

        replay = APIClient()
        replay.cookies[COOKIE] = token
        assert replay.post("/api/v1/auth/refresh/").status_code == 401

    def test_garbage_bearer_token_is_rejected(self):
        resp = bearer("not-a-jwt").get("/api/v1/me/")
        assert resp.status_code == 401


class TestMe:
    def test_requires_auth(self, api_client):
        assert api_client.get("/api/v1/me/").status_code == 401

    def test_read_and_update_language_only(self, api_client):
        access = register(api_client).data["access"]
        client = bearer(access)
        resp = client.patch("/api/v1/me/", {"language": "en", "email": "evil@example.com"}, format="json")
        assert resp.status_code == 200
        assert resp.data["language"] == "en"
        assert resp.data["email"] == "ali@example.com"

    def test_tasks_are_owned_by_the_account(self, api_client, png_upload):
        access = register(api_client).data["access"]
        client = bearer(access)
        task = client.post(
            "/api/v1/tasks/",
            {"tool": "image-convert", "options": '{"target": "jpg"}', "files": [png_upload()]},
            format="multipart",
        )
        assert task.status_code == 202
        assert Task.objects.get(pk=task.data["id"]).user.email == "ali@example.com"
        assert client.get(f"/api/v1/tasks/{task.data['id']}/").status_code == 200
        assert client.get("/api/v1/usage/").data["role"] == "registered"


class TestDeleteAccount:
    def test_wrong_password(self, api_client):
        client = bearer(register(api_client).data["access"])
        resp = client.delete("/api/v1/me/", {"password": "nope"}, format="json")
        assert resp.status_code == 403
        assert User.objects.count() == 1

    def test_deletes_user_tasks_files_and_sessions(
        self, api_client, png_upload, media_root, django_capture_on_commit_callbacks
    ):
        reg = register(api_client)
        refresh = api_client.cookies[COOKIE].value
        client = bearer(reg.data["access"])
        with django_capture_on_commit_callbacks(execute=True):
            task_id = client.post(
                "/api/v1/tasks/",
                {"tool": "image-convert", "options": '{"target": "jpg"}', "files": [png_upload()]},
                format="multipart",
            ).data["id"]
        assert list(Path(media_root).glob(f"tasks/{task_id}/**/*.*"))

        resp = client.delete("/api/v1/me/", {"password": PASSWORD}, format="json")

        assert resp.status_code == 204
        assert not User.objects.exists()
        assert not Task.objects.exists()
        assert not UsageCounter.objects.filter(subject__startswith="u:").exists()
        assert not list(Path(media_root).glob(f"tasks/{task_id}/**/*.*"))
        replay = APIClient()
        replay.cookies[COOKIE] = refresh
        assert replay.post("/api/v1/auth/refresh/").status_code == 401


class TestDeleteGoogleAccount:
    """An access token alone (say, stolen through XSS) must not delete a passwordless account."""

    TARGET = "apps.users.views.google.verify_credential"

    @pytest.fixture
    def client(self, db):
        user = User.objects.create_user(email="ali@gmail.com", password=None, email_verified=True)
        return bearer(issue_tokens(user)[0])

    def delete(self, client, identity=None, error=None, **body):
        with mock.patch(self.TARGET, return_value=identity, side_effect=error):
            return client.delete("/api/v1/me/", body, format="json")

    def test_access_token_alone_is_not_enough(self, client):
        resp = self.delete(client)
        assert resp.status_code == 403
        assert resp.data["error"]["code"] == "reauth_required"
        assert User.objects.exists()

    def test_fresh_google_confirmation_deletes(self, client):
        identity = GoogleIdentity(email="ali@gmail.com", subject="1", issued_at=int(time.time()))
        assert self.delete(client, identity, google_credential="cred").status_code == 204
        assert not User.objects.exists()

    @pytest.mark.parametrize(
        ("identity", "error", "code"),
        [
            (GoogleIdentity("bob@gmail.com", "2", int(time.time())), None, "google_account_mismatch"),
            (GoogleIdentity("ali@gmail.com", "1", int(time.time()) - 3600), None, "reauth_required"),
            (None, GoogleTokenError("bad"), "google_failed"),
        ],
    )
    def test_rejects_other_stale_or_invalid_google_sign_in(self, client, identity, error, code):
        resp = self.delete(client, identity, error, google_credential="cred")
        assert resp.status_code == 403
        assert resp.data["error"]["code"] == code
        assert User.objects.exists()

    def test_password_field_does_not_help_a_passwordless_account(self, client):
        assert self.delete(client, password="guess-anything").status_code == 403


class TestPasswordReset:
    def request_reset(self, client, email, capture):
        with capture(execute=True):
            return client.post("/api/v1/auth/password/reset/", {"email": email, "language": "uz"}, format="json")

    def reset_link_parts(self) -> tuple[str, str]:
        match = re.search(r"/uz/reset/([^/]+)/([^\s/]+)", mail.outbox[-1].body)
        assert match
        return match.group(1), match.group(2)

    def test_unknown_email_gets_same_answer_and_no_mail(self, api_client, django_capture_on_commit_callbacks):
        resp = self.request_reset(api_client, "ghost@example.com", django_capture_on_commit_callbacks)
        assert resp.status_code == 202
        assert mail.outbox == []

    def test_full_reset_flow(self, api_client, django_capture_on_commit_callbacks):
        register(api_client)
        old_refresh = api_client.cookies[COOKIE].value
        resp = self.request_reset(APIClient(), "ALI@example.com", django_capture_on_commit_callbacks)
        assert resp.status_code == 202
        assert mail.outbox[0].to == ["ali@example.com"]
        assert "parolni tiklash" in mail.outbox[0].subject
        uid, token = self.reset_link_parts()

        confirm = {"uid": uid, "token": token, "new_password": "An0ther-strong-pass"}
        resp = APIClient().post("/api/v1/auth/password/reset/confirm/", confirm, format="json")
        assert resp.status_code == 200
        assert resp.data["user"]["email_verified"] is True
        assert login(APIClient(), password="An0ther-strong-pass").status_code == 200

        # Link is single-use, and every older session was ended.
        again = APIClient().post("/api/v1/auth/password/reset/confirm/", confirm, format="json")
        assert again.data["error"]["code"] == "invalid_reset_link"
        replay = APIClient()
        replay.cookies[COOKIE] = old_refresh
        assert replay.post("/api/v1/auth/refresh/").status_code == 401

    def test_weak_new_password_rejected(self, api_client, django_capture_on_commit_callbacks):
        register(api_client)
        self.request_reset(APIClient(), "ali@example.com", django_capture_on_commit_callbacks)
        uid, token = self.reset_link_parts()
        resp = APIClient().post(
            "/api/v1/auth/password/reset/confirm/",
            {"uid": uid, "token": token, "new_password": "password"},
            format="json",
        )
        assert resp.data["error"]["code"] == "weak_password"

    def test_garbage_link(self, api_client):
        resp = api_client.post(
            "/api/v1/auth/password/reset/confirm/",
            {"uid": "zzz", "token": "x", "new_password": "An0ther-pass"},
            format="json",
        )
        assert resp.status_code == 400
        assert resp.data["error"]["code"] == "invalid_reset_link"


class TestGoogle:
    URL = "/api/v1/auth/google/"

    def post(self, client, identity=None, error=None):
        target = "apps.users.views.google.verify_credential"
        with mock.patch(target, side_effect=error, return_value=identity):
            return client.post(self.URL, {"credential": "token"}, format="json")

    def test_disabled_without_client_id(self, api_client, settings):
        settings.GOOGLE_CLIENT_ID = ""
        assert api_client.post(self.URL, {"credential": "x"}, format="json").status_code == 404

    def test_creates_verified_passwordless_account(self, api_client):
        resp = self.post(api_client, GoogleIdentity(email="new@gmail.com", subject="1"))
        assert resp.status_code == 200
        user = User.objects.get(email="new@gmail.com")
        assert user.email_verified and not user.has_usable_password()
        assert resp.data["user"]["has_password"] is False

    def test_invalid_token(self, api_client):
        resp = self.post(api_client, error=GoogleTokenError("bad"))
        assert resp.status_code == 401
        assert resp.data["error"]["code"] == "google_failed"

    def test_takes_over_unverified_squatted_account(self, api_client):
        """Someone registered the victim's address first; the real owner signs in with Google."""
        squatter = APIClient()
        register(squatter, email="victim@gmail.com")
        squatter_refresh = squatter.cookies[COOKIE].value

        resp = self.post(api_client, GoogleIdentity(email="victim@gmail.com", subject="2"))

        assert resp.status_code == 200
        assert login(APIClient(), email="victim@gmail.com").status_code == 401  # squatter's password is gone
        replay = APIClient()
        replay.cookies[COOKIE] = squatter_refresh
        assert replay.post("/api/v1/auth/refresh/").status_code == 401

    def test_verified_account_keeps_its_password(self, api_client):
        UserFactory(email="known@gmail.com", email_verified=True)
        self.post(api_client, GoogleIdentity(email="known@gmail.com", subject="3"))
        assert User.objects.get(email="known@gmail.com").has_usable_password()

    def test_disabled_account(self, api_client):
        UserFactory(email="off@gmail.com", is_active=False)
        resp = self.post(api_client, GoogleIdentity(email="off@gmail.com", subject="4"))
        assert resp.status_code == 403


class TestAuthThrottle:
    def test_parses_minute_multiples(self):
        assert AuthRateThrottle().parse_rate("10/15m") == (10, 900)
        assert AuthRateThrottle().parse_rate("5/h") == (5, 3600)

    def test_blocks_after_limit(self, api_client):
        from django.core.cache import cache

        cache.clear()
        # DRF snapshots throttle rates into a class attribute at import time.
        with mock.patch.object(AuthRateThrottle, "THROTTLE_RATES", {"auth": "3/15m"}):
            codes = [login(api_client, password="wrong-pass-1").status_code for _ in range(4)]
        assert codes == [401, 401, 401, 429]
