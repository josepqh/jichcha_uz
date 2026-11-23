import json

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient

from apps.conversions.identity import _hash
from apps.conversions.models import Task
from tests.conftest import make_image_bytes

pytestmark = pytest.mark.django_db
SECRET = "test-bot-secret-0123456789"


@pytest.fixture(autouse=True)
def bot_secret(settings):
    settings.BOT_API_SECRET = SECRET


def bot(telegram_id: int, secret: str = SECRET) -> APIClient:
    return APIClient(HTTP_X_BOT_SECRET=secret, HTTP_X_TELEGRAM_USER_ID=str(telegram_id))


def post(client):
    files = [SimpleUploadedFile("a.png", make_image_bytes())]
    return client.post(
        "/api/v1/tasks/", {"tool": "image-convert", "options": json.dumps({"target": "jpg"}), "files": files}
    )


def test_bot_acts_as_one_guest_per_telegram_user():
    resp = post(bot(111))
    assert resp.status_code == 202
    task = Task.objects.get(pk=resp.data["id"])
    assert task.user is None and task.guest_key == _hash("tg:111")
    assert "jichcha_guest" not in resp.cookies  # the bot never gets a browser cookie
    assert bot(111).get(f"/api/v1/tasks/{task.pk}/").status_code == 200
    assert bot(222).get(f"/api/v1/tasks/{task.pk}/").status_code == 404  # another Telegram user


@pytest.mark.parametrize("secret", ["wrong-secret", ""])
def test_wrong_or_missing_secret_is_just_an_anonymous_visitor(secret):
    resp = post(bot(111, secret=secret))
    assert resp.status_code == 202
    assert Task.objects.get(pk=resp.data["id"]).guest_key != _hash("tg:111")


def test_bot_identity_is_off_without_a_configured_secret(settings):
    settings.BOT_API_SECRET = ""
    resp = post(bot(111, secret=""))
    assert Task.objects.get(pk=resp.data["id"]).guest_key != _hash("tg:111")


@pytest.mark.parametrize("raw", ["0", "-5", "12abc", "1" * 17, "1;DROP"])
def test_malformed_telegram_ids_are_ignored(raw):
    client = APIClient(HTTP_X_BOT_SECRET=SECRET, HTTP_X_TELEGRAM_USER_ID=raw)
    resp = post(client)
    assert Task.objects.get(pk=resp.data["id"]).guest_key != _hash(f"tg:{raw}")


def test_daily_limit_is_per_telegram_user():
    from apps.conversions.models import LimitPolicy

    LimitPolicy.objects.filter(role="guest").update(daily_tasks=1)
    assert post(bot(111)).status_code == 202
    assert post(bot(111)).status_code == 429
    assert post(bot(222)).status_code == 202


def test_ip_ceilings_do_not_apply_to_the_bot(settings):
    """Every Telegram user reaches the backend from the bot's one IP."""
    from unittest import mock

    from apps.conversions.throttles import (
        AnonIPRateThrottle,
        GuestRateThrottle,
        GuestTaskCreateIPThrottle,
        TaskCreateThrottle,
    )

    rates = {"task_create": "100/min", "task_create_ip": "1/min", "anon": "100/min", "anon_ip": "1/min"}
    with (
        mock.patch.object(TaskCreateThrottle, "THROTTLE_RATES", rates),
        mock.patch.object(GuestTaskCreateIPThrottle, "THROTTLE_RATES", rates),
        mock.patch.object(GuestRateThrottle, "THROTTLE_RATES", rates),
        mock.patch.object(AnonIPRateThrottle, "THROTTLE_RATES", rates),
    ):
        codes = [post(bot(1000 + i)).status_code for i in range(3)]
    assert codes == [202, 202, 202]
