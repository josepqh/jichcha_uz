"""Server load for the admin panel (F-72): queues, workers, storage. Every probe fails soft."""

import logging
import shutil
from pathlib import Path

import redis
from django.conf import settings
from django.db.models import Sum

from apps.conversions.models import Task, TaskFile

logger = logging.getLogger(__name__)
QUEUES = ("light", "office", "maintenance")


def queue_lengths() -> dict[str, int | None]:
    """Messages waiting in each Celery queue (the Redis broker keeps one list per queue)."""
    try:
        client = redis.Redis.from_url(settings.CELERY_BROKER_URL, socket_timeout=2)
        return {name: int(client.llen(name)) for name in QUEUES}
    except redis.RedisError:
        logger.warning("Admin load: broker unreachable")
        return dict.fromkeys(QUEUES)


def workers() -> list[dict]:
    """Workers that answered a ping within a second."""
    from config.celery import app

    try:
        replies = app.control.inspect(timeout=1.0).ping() or {}
    except Exception:  # noqa: BLE001 - broker down shows as "no workers"
        logger.warning("Admin load: worker ping failed")
        replies = {}
    return [{"name": name, "ok": reply.get("ok") == "pong"} for name, reply in sorted(replies.items())]


def storage() -> dict:
    stored = TaskFile.objects.filter(task__files_purged_at__isnull=True).aggregate(total=Sum("size_bytes"))["total"]
    data = {"files_bytes": stored or 0, "disk_total": None, "disk_free": None}
    if not settings.USE_S3:
        path = Path(settings.MEDIA_ROOT)
        while not path.exists() and path != path.parent:
            path = path.parent
        try:
            usage = shutil.disk_usage(path)
            data |= {"disk_total": usage.total, "disk_free": usage.free}
        except OSError:
            pass
    return data


def snapshot() -> dict:
    return {
        "queues": queue_lengths(),
        "workers": workers(),
        "tasks": {
            "queued": Task.objects.filter(status=Task.Status.QUEUED).count(),
            "processing": Task.objects.filter(status=Task.Status.PROCESSING).count(),
        },
        "storage": storage(),
    }
