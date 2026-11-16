from datetime import timedelta
from unittest import mock

import pytest
from django.utils import timezone

from apps.conversions.models import Task
from apps.staff import monitoring
from apps.staff.management.commands import monitor


@pytest.fixture
def sent():
    with mock.patch.object(monitor, "send", return_value=True) as fake:
        yield fake


def test_alerts_once_per_change_and_on_recovery(sent):
    problem = {"value": "Disk almost full."}
    checks = {"disk": lambda: problem["value"], "fine": lambda: None}
    state: dict = {}
    with mock.patch.object(monitor, "CHECKS", checks):
        assert len(monitor.run_checks(state, "test")) == 1  # starts failing
        assert monitor.run_checks(state, "test") == []  # still failing: silence
        problem["value"] = None
        [recovered] = monitor.run_checks(state, "test")
    assert "disk is OK again" in recovered
    assert sent.call_count == 2


def test_a_crashing_check_is_reported(sent):
    def broken():
        raise RuntimeError("boom")

    with mock.patch.object(monitor, "CHECKS", {"workers": broken}):
        [message] = monitor.run_checks({}, "test")
    assert "Check crashed: RuntimeError" in message


def test_send_without_configuration_just_logs(settings):
    settings.ALERT_TELEGRAM_CHAT_ID = ""
    assert monitor.send("hi") is False


def test_send_posts_to_the_team_chat(settings):
    settings.ALERT_TELEGRAM_TOKEN, settings.ALERT_TELEGRAM_CHAT_ID = "1:abc", "-100500"
    with mock.patch.object(monitor.requests, "post", return_value=mock.Mock(ok=True)) as post:
        assert monitor.send("hello") is True
    assert post.call_args.kwargs["json"]["chat_id"] == "-100500"


@pytest.mark.django_db
def test_error_rate(settings):
    settings.ALERT_MIN_TASKS, settings.ALERT_ERROR_RATE = 4, 0.3
    now = timezone.now()
    for status in ["failed", "failed", "done", "done"]:
        Task.objects.create(
            guest_key="g", tool="pdf-merge", status=status, finished_at=now, expires_at=now + timedelta(hours=1)
        )
    assert "2 of 4 tasks failed" in monitoring.error_rate()
    settings.ALERT_MIN_TASKS = 10  # too few tasks to judge
    assert monitoring.error_rate() is None


def test_queue_and_worker_checks(settings):
    settings.ALERT_QUEUE_MAX = 50
    with mock.patch.object(monitoring.load, "queue_lengths", return_value={"light": 80, "office": 1}):
        assert "light" in monitoring.queues()
    with mock.patch.object(monitoring.load, "queue_lengths", return_value={"light": None}):
        assert "broker" in monitoring.queues()
    with mock.patch.object(monitoring.load, "workers", return_value=[]):
        assert "No Celery worker" in monitoring.workers()


def test_antivirus_check(settings):
    settings.CLAMAV_HOST = ""
    assert monitoring.antivirus_daemon() is None  # scanning off
    settings.CLAMAV_HOST, settings.CLAMAV_PORT = "127.0.0.1", 1
    assert "ClamAV" in monitoring.antivirus_daemon()
