import ctypes
import os
import sys

from celery import Celery
from celery.signals import worker_init, worker_process_init

os.environ.setdefault("DJANGO_SETTINGS_MODULE", "config.settings.development")

app = Celery("universe")
app.config_from_object("django.conf:settings", namespace="CELERY")
app.autodiscover_tasks()

_PR_SET_DUMPABLE = 4


def make_undumpable() -> bool:
    """Hide this process's /proc/<pid>/environ and memory from same-user processes (Linux only).

    Converters (LibreOffice) run as the same user as the worker. A crafted document that
    makes them read local files must not be able to read the worker's environment, which holds
    the database URL and the secret key. Non-dumpable processes have their /proc files owned by root.
    """
    if not sys.platform.startswith("linux"):
        return False
    libc = ctypes.CDLL(None, use_errno=True)
    return libc.prctl(_PR_SET_DUMPABLE, 0, 0, 0, 0) == 0


@worker_init.connect
@worker_process_init.connect
def _harden_worker(**_kwargs) -> None:
    make_undumpable()
