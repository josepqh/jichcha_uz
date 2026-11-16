import tempfile
from pathlib import Path

from celery import shared_task

from . import services


@shared_task(acks_late=True, ignore_result=True)
def run_conversion(task_id: str, secrets: dict | None = None) -> None:
    with tempfile.TemporaryDirectory(prefix="uv-task-") as tmp:
        services.process_task(task_id, Path(tmp), secrets)


@shared_task(ignore_result=True)
def purge_expired() -> int:
    return services.purge_expired()
