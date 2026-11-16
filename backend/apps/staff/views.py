"""Admin panel API (F-70 – F-75). Staff only; every change is logged with the acting admin."""

import logging
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db import transaction
from django.db.models import Count, Q
from django.shortcuts import get_object_or_404
from django.utils import timezone
from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser
from rest_framework.request import Request
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.conversions.models import LimitPolicy, Task, ToolSetting
from apps.conversions.tools import TOOLS
from apps.core.exceptions import AppError
from apps.users.tokens import revoke_all_sessions

from . import load, stats
from .serializers import FailedTaskSerializer, LimitPolicySerializer, StaffUserSerializer

logger = logging.getLogger("apps.staff.audit")
User = get_user_model()


class StaffView(APIView):
    permission_classes = [IsAdminUser]


class Pagination(PageNumberPagination):
    page_size = 25


class DashboardView(StaffView):
    def get(self, request: Request) -> Response:
        days = 30 if request.query_params.get("days") == "30" else 7
        return Response(stats.dashboard(days))


class LoadView(StaffView):
    def get(self, request: Request) -> Response:
        return Response(load.snapshot())


class UserListView(StaffView):
    def get(self, request: Request) -> Response:
        since = timezone.now() - timedelta(days=30)
        users = User.objects.annotate(tasks_30d=Count("tasks", filter=Q(tasks__created_at__gte=since))).order_by(
            "-date_joined"
        )
        if query := request.query_params.get("q", "").strip()[:254]:
            users = users.filter(email__icontains=query)
        if request.query_params.get("blocked") == "1":
            users = users.filter(is_active=False)
        paginator = Pagination()
        page = paginator.paginate_queryset(users, request, view=self)
        return paginator.get_paginated_response(StaffUserSerializer(page, many=True).data)


class UserBlockView(StaffView):
    """POST blocks (signs the user out everywhere), DELETE unblocks."""

    def _target(self, request: Request, user_id) -> User:
        user = get_object_or_404(User, pk=user_id)
        if user.pk == request.user.pk:
            raise AppError("cannot_block_self", "You can't block yourself.", status.HTTP_403_FORBIDDEN)
        if user.is_staff or user.is_superuser:
            raise AppError("cannot_block_staff", "Staff accounts can't be blocked here.", status.HTTP_403_FORBIDDEN)
        return user

    def post(self, request: Request, user_id) -> Response:
        user = self._target(request, user_id)
        with transaction.atomic():
            user.is_active = False
            user.save(update_fields=["is_active"])
            revoke_all_sessions(user)
        logger.info("admin=%s blocked user=%s", request.user.pk, user.pk)
        return Response(StaffUserSerializer(user).data)

    def delete(self, request: Request, user_id) -> Response:
        user = self._target(request, user_id)
        user.is_active = True
        user.save(update_fields=["is_active"])
        logger.info("admin=%s unblocked user=%s", request.user.pk, user.pk)
        return Response(StaffUserSerializer(user).data)


class FailureListView(StaffView):
    def get(self, request: Request) -> Response:
        since = timezone.now() - timedelta(days=30)
        failed = Task.objects.filter(status=Task.Status.FAILED, created_at__gte=since)
        summary = list(failed.values("tool", "error_code").annotate(count=Count("id")).order_by("-count", "tool")[:20])
        if tool := request.query_params.get("tool"):
            failed = failed.filter(tool=tool)
        if code := request.query_params.get("code"):
            failed = failed.filter(error_code=code)
        paginator = Pagination()
        page = paginator.paginate_queryset(failed.order_by("-created_at"), request, view=self)
        response = paginator.get_paginated_response(FailedTaskSerializer(page, many=True).data)
        response.data["summary"] = summary
        return response


class LimitListView(StaffView):
    def get(self, request: Request) -> Response:
        return Response(LimitPolicySerializer(LimitPolicy.objects.order_by("role"), many=True).data)


class LimitDetailView(StaffView):
    def patch(self, request: Request, role: str) -> Response:
        policy = get_object_or_404(LimitPolicy, role=role)
        serializer = LimitPolicySerializer(policy, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        logger.info("admin=%s changed limits role=%s %s", request.user.pk, role, serializer.validated_data)
        return Response(serializer.data)


class ToolSwitchListView(StaffView):
    def get(self, request: Request) -> Response:
        off = set(ToolSetting.objects.filter(enabled=False).values_list("slug", flat=True))
        return Response([{"slug": slug, "enabled": slug not in off} for slug in TOOLS])


class ToolSwitchView(StaffView):
    def patch(self, request: Request, slug: str) -> Response:
        if slug not in TOOLS:
            raise AppError("unknown_tool", "Unknown tool.", status.HTTP_404_NOT_FOUND)
        enabled = request.data.get("enabled")
        if not isinstance(enabled, bool):
            raise AppError("validation_error", "enabled must be true or false.", details={"enabled": ["Required."]})
        ToolSetting.objects.update_or_create(slug=slug, defaults={"enabled": enabled})
        logger.info("admin=%s set tool=%s enabled=%s", request.user.pk, slug, enabled)
        return Response({"slug": slug, "enabled": enabled})
