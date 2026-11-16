"""Checks behind the alerting loop (`manage.py monitor`). Each returns a problem text, or None when fine."""

import socket
from datetime import timedelta

from django.conf import settings
from django.utils import timezone

from apps.conversions import antivirus
from apps.conversions.models import Task
from apps.core.health import _cache, _database, _disk

from . import load


def database() -> str | None:
    return None if _database() else "Database is not answering."


def cache() -> str | None:
    return None if _cache() else "Redis is not answering."


def disk() -> str | None:
    return None if _disk() else f"Less than {settings.HEALTH_MIN_FREE_MB} MB free on the media disk."


def queues() -> str | None:
    lengths = load.queue_lengths()
    if all(v is None for v in lengths.values()):
        return "Cannot read the task queues (broker down?)."
    long = {name: n for name, n in lengths.items() if n is not None and n > settings.ALERT_QUEUE_MAX}
    return f"Queues are backing up: {long}." if long else None


def workers() -> str | None:
    found = load.workers()
    if not found:
        return "No Celery worker answered a ping."
    down = [w["name"] for w in found if not w["ok"]]
    return f"Workers not answering: {', '.join(down)}." if down else None


def antivirus_daemon() -> str | None:
    if not antivirus.enabled():
        return None
    try:
        with socket.create_connection((settings.CLAMAV_HOST, settings.CLAMAV_PORT), timeout=5) as sock:
            sock.sendall(b"zPING\0")
            if sock.recv(16).rstrip(b"\0") == b"PONG":
                return None
    except OSError:
        pass
    return "ClamAV is not answering: uploads fail with scan_unavailable."


def error_rate() -> str | None:
    since = timezone.now() - timedelta(minutes=15)
    recent = Task.objects.filter(finished_at__gte=since)
    total = recent.count()
    failed = recent.filter(status=Task.Status.FAILED).count()
    if total >= settings.ALERT_MIN_TASKS and failed / total > settings.ALERT_ERROR_RATE:
        return f"{failed} of {total} tasks failed in the last 15 minutes."
    return None


CHECKS = {
    "database": database,
    "cache": cache,
    "disk": disk,
    "queues": queues,
    "workers": workers,
    "antivirus": antivirus_daemon,
    "error_rate": error_rate,
}
