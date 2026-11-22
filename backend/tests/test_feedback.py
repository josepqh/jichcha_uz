import pytest
from django.core import mail
from rest_framework.test import APIClient

pytestmark = pytest.mark.django_db

URL = "/api/v1/feedback/"


def send(payload, capture):
    with capture(execute=True):
        return APIClient().post(URL, payload, format="json")


def test_suggestion_is_emailed_with_reply_to(django_capture_on_commit_callbacks, settings):
    settings.FEEDBACK_EMAIL = "team@example.com"
    payload = {"message": "Please add PDF to Word.", "email": "ali@example.com", "language": "uz"}
    assert send(payload, django_capture_on_commit_callbacks).status_code == 202
    [message] = mail.outbox
    assert message.to == ["team@example.com"]
    assert message.reply_to == ["ali@example.com"]
    assert message.subject == "jichcha: feedback (uz)"
    assert "Please add PDF to Word." in message.body


def test_default_address_and_anonymous_complaints(django_capture_on_commit_callbacks):
    assert (
        send(
            {"message": "The download did not start."}, django_capture_on_commit_callbacks
        ).status_code
        == 202
    )
    assert mail.outbox[0].to == ["jichchainfo@gmail.com"]
    assert mail.outbox[0].reply_to == []


@pytest.mark.parametrize(
    ("payload", "field"),
    [
        ({"message": "short"}, "message"),
        ({"message": "long enough message", "email": "not-an-email"}, "email"),
    ],
)
def test_validation(payload, field):
    resp = APIClient().post(URL, payload, format="json")
    assert resp.status_code == 400
    assert field in resp.data["error"]["details"]


def test_honeypot_looks_fine_but_sends_nothing(django_capture_on_commit_callbacks):
    payload = {"message": "Buy cheap things here", "website": "http://spam.example"}
    assert send(payload, django_capture_on_commit_callbacks).status_code == 202
    assert mail.outbox == []


def test_rate_limited_per_ip(monkeypatch):
    from apps.core.feedback import FeedbackThrottle

    monkeypatch.setattr(FeedbackThrottle, "rate", "2/1h", raising=False)
    client = APIClient()
    payload = {"message": "a real question here"}
    codes = [client.post(URL, payload, format="json").status_code for _ in range(3)]
    assert codes == [202, 202, 429]
