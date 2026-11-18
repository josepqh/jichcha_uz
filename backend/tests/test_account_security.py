"""Two-step sign-in, password change, email confirmation and the staff 2FA gate."""

import re
import time
from unittest import mock

import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.users import totp
from apps.users.google import GoogleIdentity
from apps.users.models import User
from apps.users.verification import make_token
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"
COOKIE = "uv_refresh"


def signed_in(user: User) -> APIClient:
    client = APIClient()
    client.force_authenticate(user=user)
    return client


def current_code(secret: str, offset: int = 0) -> str:
    return totp.code_at(secret, int(time.time() // totp.STEP) + offset)


def with_2fa(**extra) -> User:
    user = UserFactory(email_verified=True, **extra)
    user.set_password(PASSWORD)
    user.totp_secret = totp.new_secret()
    user.totp_enabled = True
    user.save()
    return user


def login(client, email, password=PASSWORD, **extra):
    return client.post("/api/v1/auth/login/", {"email": email, "password": password, **extra}, format="json")


class TestTotpMath:
    def test_rfc6238_vector(self):
        # RFC 6238 appendix B, SHA-1 secret "12345678901234567890", T = 59 s -> 94287082 (8 digits).
        secret = "GEZDGNBVGY3TQOJQGEZDGNBVGY3TQOJQ"
        assert totp.code_at(secret, 59 // 30) == "287082"

    def test_accepts_one_step_of_drift_only(self):
        secret = totp.new_secret()
        now = time.time()
        step = int(now // totp.STEP)
        assert totp.matching_step(secret, totp.code_at(secret, step - 1), now) == step - 1
        assert totp.matching_step(secret, totp.code_at(secret, step + 2), now) is None
        assert totp.matching_step(secret, "12 34 5", now) is None
        assert totp.matching_step("", "123456", now) is None


class TestSetup:
    def test_full_setup_then_login_needs_a_code(self):
        user = UserFactory(email_verified=True)
        user.set_password(PASSWORD)
        user.save()
        client = signed_in(user)

        setup = client.post("/api/v1/me/2fa/setup/")
        assert setup.status_code == 200
        assert setup.data["otpauth_uri"].startswith("otpauth://totp/Universe%3A")
        assert setup.data["qr"].startswith("data:image/svg+xml")
        secret = setup.data["secret"]

        assert client.post("/api/v1/me/2fa/enable/", {"code": "000000"}).data["error"]["code"] == "otp_invalid"
        resp = client.post("/api/v1/me/2fa/enable/", {"code": current_code(secret)})
        assert resp.status_code == 200 and resp.data["totp_enabled"] is True

        no_code = login(APIClient(), user.email)
        assert (no_code.status_code, no_code.data["error"]["code"]) == (401, "otp_required")
        assert COOKIE not in no_code.cookies  # no session before the second step

        # The code used to switch it on cannot be used again.
        assert login(APIClient(), user.email, otp=current_code(secret)).data["error"]["code"] == "otp_invalid"

    def test_needs_a_confirmed_email(self, user_client):
        resp = user_client.post("/api/v1/me/2fa/setup/")
        assert (resp.status_code, resp.data["error"]["code"]) == (403, "email_unverified")

    def test_enable_without_setup(self):
        resp = signed_in(UserFactory(email_verified=True)).post("/api/v1/me/2fa/enable/", {"code": "123456"})
        assert resp.data["error"]["code"] == "otp_not_started"


class TestLoginWithCode:
    def test_right_code_signs_in_and_works_once(self):
        user = with_2fa()
        code = current_code(user.totp_secret)
        resp = login(APIClient(), user.email, otp=code)
        assert resp.status_code == 200 and resp.data["user"]["totp_enabled"] is True
        assert login(APIClient(), user.email, otp=code).data["error"]["code"] == "otp_invalid"

    def test_wrong_password_never_reaches_the_code_step(self):
        user = with_2fa()
        resp = login(APIClient(), user.email, password="wrong-pass-1", otp="")
        assert resp.data["error"]["code"] == "invalid_credentials"

    def test_too_many_wrong_codes_lock_the_account_for_a_while(self):
        user = with_2fa()
        for _ in range(totp.MAX_FAILURES):
            assert login(APIClient(), user.email, otp="000000").data["error"]["code"] == "otp_invalid"
        resp = login(APIClient(), user.email, otp=current_code(user.totp_secret))
        assert (resp.status_code, resp.data["error"]["code"]) == (429, "otp_locked")

    def test_google_sign_in_also_asks_for_the_code(self):
        user = with_2fa()
        identity = GoogleIdentity(email=user.email, subject="g-1", issued_at=int(time.time()))
        with mock.patch("apps.users.google.verify_credential", return_value=identity):
            first = APIClient().post("/api/v1/auth/google/", {"credential": "x"}, format="json")
            second = APIClient().post(
                "/api/v1/auth/google/", {"credential": "x", "otp": current_code(user.totp_secret)}, format="json"
            )
        assert first.data["error"]["code"] == "otp_required"
        assert second.status_code == 200

    def test_google_owner_takes_back_a_squatted_account_with_2fa(self):
        squatted = with_2fa()
        User.objects.filter(pk=squatted.pk).update(email_verified=False)
        identity = GoogleIdentity(email=squatted.email, subject="g-2", issued_at=int(time.time()))
        with mock.patch("apps.users.google.verify_credential", return_value=identity):
            resp = APIClient().post("/api/v1/auth/google/", {"credential": "x"}, format="json")
        assert resp.status_code == 200
        squatted.refresh_from_db()
        assert (squatted.totp_enabled, squatted.totp_secret) == (False, "")

    def test_password_reset_link_alone_does_not_skip_the_code(self):
        from django.contrib.auth.tokens import default_token_generator
        from django.utils.encoding import force_bytes
        from django.utils.http import urlsafe_base64_encode

        user = with_2fa()
        payload = {
            "uid": urlsafe_base64_encode(force_bytes(user.pk)),
            "token": default_token_generator.make_token(user),
            "new_password": "An0ther-strong-pass",
        }
        resp = APIClient().post("/api/v1/auth/password/reset/confirm/", payload, format="json")
        assert resp.data["error"]["code"] == "otp_required"
        user.refresh_from_db()
        assert user.check_password(PASSWORD)  # unchanged, and the link still works with the code

        payload["otp"] = current_code(user.totp_secret)
        assert APIClient().post("/api/v1/auth/password/reset/confirm/", payload, format="json").status_code == 200


class TestDisable:
    def test_needs_password_and_code(self):
        user = with_2fa()
        client = signed_in(user)
        code = current_code(user.totp_secret)
        wrong_pw = client.post("/api/v1/me/2fa/disable/", {"password": "nope", "code": code})
        assert wrong_pw.data["error"]["code"] == "invalid_credentials"
        resp = client.post("/api/v1/me/2fa/disable/", {"password": PASSWORD, "code": code})
        assert resp.status_code == 200 and resp.data["totp_enabled"] is False
        user.refresh_from_db()
        assert user.totp_secret == ""
        assert login(APIClient(), user.email).status_code == 200


class TestPasswordChange:
    def test_change_ends_other_sessions_and_keeps_this_one(self):
        client = APIClient()
        client.post("/api/v1/auth/register/", {"email": "ali@example.com", "password": PASSWORD}, format="json")
        other_device = client.cookies[COOKIE].value
        access = client.post("/api/v1/auth/refresh/").data["access"]
        client.credentials(HTTP_AUTHORIZATION=f"Bearer {access}")

        resp = client.post(
            "/api/v1/me/password/", {"current_password": PASSWORD, "new_password": "An0ther-strong-pass"}, format="json"
        )
        assert resp.status_code == 200 and resp.data["access"]
        assert client.cookies[COOKIE].value  # fresh session for this tab

        from django.core.cache import cache

        cache.clear()  # past the refresh grace period
        replay = APIClient()
        replay.cookies[COOKIE] = other_device
        assert replay.post("/api/v1/auth/refresh/").status_code == 401
        assert login(APIClient(), "ali@example.com", password="An0ther-strong-pass").status_code == 200

    def test_wrong_current_or_weak_new(self):
        user = UserFactory()
        user.set_password(PASSWORD)
        user.save()
        client = signed_in(user)
        wrong = client.post("/api/v1/me/password/", {"current_password": "x", "new_password": "An0ther-strong-pass"})
        assert (wrong.status_code, wrong.data["error"]["code"]) == (403, "invalid_credentials")
        weak = client.post("/api/v1/me/password/", {"current_password": PASSWORD, "new_password": "12345678"})
        assert weak.data["error"]["code"] == "weak_password"

    def test_google_only_account_has_no_current_password(self):
        user = UserFactory(password=None)
        resp = signed_in(user).post("/api/v1/me/password/", {"current_password": "", "new_password": "An0ther-pass-9"})
        assert resp.status_code in (400, 403)


class TestEmailVerification:
    def test_register_sends_a_link_that_confirms_the_address(self, django_capture_on_commit_callbacks):
        with django_capture_on_commit_callbacks(execute=True):
            APIClient().post(
                "/api/v1/auth/register/",
                {"email": "vali@example.com", "password": PASSWORD, "language": "en"},
                format="json",
            )
        [message] = mail.outbox
        assert message.subject == "Universe: confirm your email"
        token = re.search(r"/en/verify-email/(\S+)", message.body).group(1)
        assert "vali@example.com" not in token

        resp = APIClient().post("/api/v1/auth/email/verify/", {"token": token}, format="json")
        assert resp.status_code == 200
        assert User.objects.get(email="vali@example.com").email_verified is True

    def test_bad_tampered_or_stale_tokens(self):
        user = UserFactory()
        token = make_token(user)
        bad = APIClient().post("/api/v1/auth/email/verify/", {"token": token[:-2] + "xx"}, format="json")
        assert bad.data["error"]["code"] == "invalid_verify_link"
        User.objects.filter(pk=user.pk).update(email="changed@example.com")  # link was for the old address
        stale = APIClient().post("/api/v1/auth/email/verify/", {"token": token}, format="json")
        assert stale.data["error"]["code"] == "invalid_verify_link"

    def test_resend(self, django_capture_on_commit_callbacks):
        user = UserFactory(language="ru")
        with django_capture_on_commit_callbacks(execute=True):
            assert signed_in(user).post("/api/v1/me/email/verify/").status_code == 202
        assert mail.outbox[0].subject == "Universe: подтвердите email"
        user.email_verified = True
        user.save()
        assert signed_in(user).post("/api/v1/me/email/verify/").data["error"]["code"] == "already_verified"


class TestStaffGate:
    def test_staff_without_2fa_are_asked_to_turn_it_on(self, settings):
        settings.STAFF_REQUIRE_2FA = True
        staff = UserFactory(is_staff=True)
        resp = signed_in(staff).get("/api/v1/admin/dashboard/")
        assert (resp.status_code, resp.data["error"]["code"]) == (403, "staff_2fa_required")
        assert signed_in(with_2fa(is_staff=True)).get("/api/v1/admin/dashboard/").status_code == 200

    def test_ordinary_users_still_get_a_plain_403(self, settings):
        settings.STAFF_REQUIRE_2FA = True
        resp = signed_in(UserFactory()).get("/api/v1/admin/dashboard/")
        assert resp.status_code == 403 and resp.data["error"]["code"] != "staff_2fa_required"


def test_django_admin_is_off_without_a_path(settings):
    from importlib import reload

    from django.urls import clear_url_caches

    import config.urls

    settings.DJANGO_ADMIN_URL = ""
    clear_url_caches()
    reload(config.urls)
    try:
        assert APIClient().get("/admin/login/").status_code == 404
    finally:
        settings.DJANGO_ADMIN_URL = "admin/"
        clear_url_caches()
        reload(config.urls)
    assert APIClient().get("/admin/login/").status_code == 200
