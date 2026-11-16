"""Liveness/readiness for load balancers and uptime monitors.

Returns only pass/fail per check (no versions, paths or sizes), so it is safe to leave public.
"""

import shutil
from pathlib import Path

from django.conf import settings
from django.core.cache import cache
from django.db import connection
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

MB = 1024 * 1024


def _database() -> bool:
    try:
        with connection.cursor() as cursor:
            cursor.execute("SELECT 1")
        return True
    except Exception:  # noqa: BLE001
        return False


def _cache() -> bool:
    try:
        cache.set("health:ping", "1", 10)
        return cache.get("health:ping") == "1"
    except Exception:  # noqa: BLE001
        return False


def _disk() -> bool:
    """Uploads and results fill MEDIA_ROOT; alert before the disk is full, not after."""
    if settings.USE_S3:
        return True
    path = Path(settings.MEDIA_ROOT)
    while not path.exists() and path != path.parent:  # created on first upload
        path = path.parent
    try:
        return shutil.disk_usage(path).free >= settings.HEALTH_MIN_FREE_MB * MB
    except OSError:
        return False


class HealthView(APIView):
    authentication_classes: list = []
    permission_classes = [AllowAny]

    def get(self, request: Request) -> Response:
        checks = {"database": _database(), "cache": _cache(), "disk": _disk()}
        healthy = all(checks.values())
        return Response(
            {"status": "ok" if healthy else "fail", "checks": checks},
            status=status.HTTP_200_OK if healthy else status.HTTP_503_SERVICE_UNAVAILABLE,
        )
