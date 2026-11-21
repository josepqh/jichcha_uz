import pytest
from django.core import mail
from rest_framework.test import APIClient

from apps.users.models import User

pytestmark = pytest.mark.django_db

PASSWORD = "Str0ng-pass-123"


@pytest.mark.parametrize(("lang", "subject"), [("ar", "jichcha: أكّد بريدك الإلكتروني"), ("ko", "jichcha: 이메일 인증")])
def test_new_languages_get_their_own_email(django_capture_on_commit_callbacks, lang, subject):
    with django_capture_on_commit_callbacks(execute=True):
        resp = APIClient().post(
            "/api/v1/auth/register/",
            {"email": f"{lang}@example.com", "password": PASSWORD, "language": lang},
            format="json",
        )
    assert resp.status_code == 201 and resp.data["user"]["language"] == lang
    assert mail.outbox[0].subject == subject
    assert f"/{lang}/verify-email/" in mail.outbox[0].body


def test_unknown_language_is_refused_and_profile_accepts_new_ones():
    resp = APIClient().post(
        "/api/v1/auth/register/", {"email": "x@example.com", "password": PASSWORD, "language": "xx"}, format="json"
    )
    assert resp.status_code == 400
    user = User.objects.create_user(email="de@example.com", password=PASSWORD)
    client = APIClient()
    client.force_authenticate(user=user)
    assert client.patch("/api/v1/me/", {"language": "de"}, format="json").data["language"] == "de"


def test_reset_email_falls_back_to_english_for_a_language_without_text(monkeypatch):
    from apps.users import emails

    user = User.objects.create_user(email="fallback@example.com", password=PASSWORD, language="ja")
    monkeypatch.delitem(emails.RESET, "ja")
    subject, _ = emails.password_reset_message(user, "ja")
    assert subject == "jichcha: reset your password"
