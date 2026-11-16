import json
from pathlib import PurePath

from django.conf import settings
from django.db.models import Q
from django.http import FileResponse, HttpResponseRedirect
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.parsers import MultiPartParser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.core.exceptions import AppError

from . import services
from .downloads import verify_download_token
from .identity import attach_guest_cookie, guest_key_from_cookie, resolve_requester
from .models import Task, TaskFile
from .serializers import TaskSerializer
from .throttles import GuestTaskCreateIPThrottle, TaskCreateThrottle
from .tools import TOOLS, get_tool


class ToolListView(APIView):
    def get(self, request: Request) -> Response:
        data = [
            {
                "slug": t.slug,
                "category": t.category,
                "accepts": sorted(t.accepts),
                "accepts_any": t.accepts_any,
                "outputs": list(t.outputs),
                "max_files": t.max_files,
                "min_files": t.min_files,
            }
            for t in TOOLS.values()
        ]
        return Response(data)


class UsageView(APIView):
    def get(self, request: Request) -> Response:
        requester = resolve_requester(request)
        policy = services.get_policy(requester.role)
        used = services.usage_today(requester) if (requester.user or requester.guest_key) else 0
        return Response(
            {
                "role": requester.role,
                "limits": {
                    "max_file_mb": policy.max_file_mb,
                    "max_total_mb": policy.max_total_mb,
                    "daily_tasks": policy.daily_tasks,
                    "max_batch": policy.max_batch,
                    "retention_hours": policy.retention_hours,
                },
                "today": {"tasks_used": used, "tasks_left": max(policy.daily_tasks - used, 0)},
            }
        )


def _owned_tasks(request: Request):
    """Tasks of the signed-in user, plus guest tasks made in this same browser (same guest cookie).

    The guest cookie is the capability for guest tasks, so a user who signs in mid-conversion keeps
    access to what they started a moment earlier as a guest.
    """
    owned = Q()
    if request.user.is_authenticated:
        owned |= Q(user=request.user)
    guest_key = guest_key_from_cookie(request)
    if guest_key:
        owned |= Q(user__isnull=True, guest_key=guest_key)
    return Task.objects.filter(owned) if owned else Task.objects.none()


class TaskCreateView(APIView):
    parser_classes = [MultiPartParser]
    throttle_classes = [TaskCreateThrottle, GuestTaskCreateIPThrottle]

    def post(self, request: Request) -> Response:
        requester = resolve_requester(request, create_guest=True)
        policy = services.get_policy(requester.role)
        # Checked before request.data is touched, so oversized bodies are never parsed.
        services.check_request_size(request.META.get("CONTENT_LENGTH"), policy)

        tool = get_tool(request.data.get("tool", ""))
        if tool is None:
            raise AppError("unknown_tool", "Unknown tool.", details={"tool": ["Unknown tool."]})
        try:
            raw_options = json.loads(request.data.get("options") or "{}")
        except json.JSONDecodeError:
            raise AppError(
                "validation_error", "Options must be JSON.", details={"options": ["Invalid JSON."]}
            ) from None
        if not isinstance(raw_options, dict):
            raise AppError(
                "validation_error", "Options must be an object.", details={"options": ["Must be an object."]}
            )
        opts = tool.options(data=raw_options)
        opts.is_valid(raise_exception=True)

        uploads = services.validate_uploads(tool, request.FILES.getlist("files"), policy)
        task = services.create_task(requester, tool, dict(opts.validated_data), uploads, policy)
        task = Task.objects.prefetch_related("files").get(pk=task.pk)
        response = Response(TaskSerializer(task).data, status=status.HTTP_202_ACCEPTED)
        return attach_guest_cookie(response, requester)


class TaskListView(APIView):
    """History is a registered-user feature."""

    def get(self, request: Request) -> Response:
        if not request.user.is_authenticated:
            raise AppError("auth_required", "Sign in to see history.", status.HTTP_401_UNAUTHORIZED)
        from rest_framework.pagination import PageNumberPagination

        paginator = PageNumberPagination()
        qs = Task.objects.filter(user=request.user).prefetch_related("files").order_by("-created_at")
        page = paginator.paginate_queryset(qs, request, view=self)
        return paginator.get_paginated_response(TaskSerializer(page, many=True).data)


class TaskDetailView(APIView):
    def get(self, request: Request, task_id) -> Response:
        task = get_object_or_404(_owned_tasks(request).prefetch_related("files"), pk=task_id)
        return Response(TaskSerializer(task).data)

    def delete(self, request: Request, task_id) -> Response:
        task = get_object_or_404(_owned_tasks(request), pk=task_id)
        services.purge_task_files(task)
        return Response(status=status.HTTP_204_NO_CONTENT)


class FileDownloadView(APIView):
    """Serves an output file to whoever holds a valid signed link (see downloads.py)."""

    authentication_classes: list = []

    def get(self, request: Request, file_id):
        if not verify_download_token(request.query_params.get("t", ""), file_id):
            raise AppError("file_expired", "The link is invalid or has expired.", status.HTTP_404_NOT_FOUND)
        tf = get_object_or_404(TaskFile.objects.select_related("task").exclude(role=TaskFile.Role.INPUT), pk=file_id)
        if tf.task.files_purged_at or tf.task.expires_at <= timezone.now():
            raise AppError("file_expired", "The file has been deleted.", status.HTTP_410_GONE)
        # Archive outputs keep folders in their name ("photos/img.jpg"); the saved file gets the last part.
        filename = PurePath(tf.original_name).name or "file"
        if settings.USE_S3:
            disposition = f"attachment; filename*=UTF-8''{_quote(filename)}"
            url = tf.file.storage.url(
                tf.file.name,
                parameters={"ResponseContentDisposition": disposition, "ResponseContentType": tf.mime_type},
            )
            return HttpResponseRedirect(url)
        response = FileResponse(tf.file.open("rb"), as_attachment=True, filename=filename, content_type=tf.mime_type)
        response["Cache-Control"] = "private, no-store"
        response["Referrer-Policy"] = "no-referrer"
        return response


def _quote(name: str) -> str:
    from urllib.parse import quote

    return quote(name, safe="")
