import json
from datetime import timedelta
from unittest import mock

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient
from rest_framework_simplejwt.token_blacklist.models import OutstandingToken

from apps.conversions.models import LimitPolicy, Task, ToolSetting
from apps.users.tokens import issue_tokens
from tests.conftest import make_image_bytes
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db
BASE = "/api/v1/admin"


@pytest.fixture
def admin():
    return UserFactory(is_staff=True)


@pytest.fixture
def admin_client(admin):
    client = APIClient()
    client.force_authenticate(user=admin)
    return client


def make_task(tool="image-convert", status="done", source="web", user=None, guest="g1", days_ago=0, code=""):
    task = Task.objects.create(
        user=user,
        guest_key="" if user else guest,
        tool=tool,
        status=status,
        source=source,
        error_code=code,
        input_meta=[{"format": "png", "size": 123}],
        expires_at=timezone.now() + timedelta(hours=1),
    )
    if days_ago:
        Task.objects.filter(pk=task.pk).update(created_at=timezone.now() - timedelta(days=days_ago))
    return task


ENDPOINTS = [
    ("get", "/dashboard/"),
    ("get", "/load/"),
    ("get", "/users/"),
    ("get", "/failures/"),
    ("get", "/limits/"),
    ("patch", "/limits/guest/"),
    ("get", "/tools/"),
    ("patch", "/tools/pdf-merge/"),
]


@pytest.mark.parametrize(("method", "path"), ENDPOINTS)
def test_only_staff_get_in(method, path, user_client):
    assert getattr(APIClient(), method)(BASE + path).status_code == 401
    assert getattr(user_client, method)(BASE + path, {}, format="json").status_code == 403


def test_block_endpoint_is_staff_only(user_client, user):
    other = UserFactory()
    assert user_client.post(f"{BASE}/users/{other.pk}/block/").status_code == 403
    other.refresh_from_db()
    assert other.is_active


class TestDashboard:
    def test_counts_tasks_errors_people_and_sources(self, admin_client):
        member = UserFactory()
        make_task(user=member)
        make_task(user=member, tool="pdf-merge", status="failed", code="corrupt_file")
        make_task(guest="browser-a")
        make_task(guest="tg-1", source="telegram")
        make_task(guest="tg-1", source="telegram")
        make_task(guest="old", days_ago=10)  # outside the 7-day window

        data = admin_client.get(f"{BASE}/dashboard/").data
        totals = data["totals"]
        assert (totals["tasks"], totals["failed"], totals["active"]) == (5, 1, 3)
        assert (totals["web_tasks"], totals["telegram_tasks"], totals["telegram_users"]) == (3, 2, 1)
        assert totals["error_rate"] == 0.2
        assert data["top_tools"][0] == {"tool": "image-convert", "count": 4, "failed": 0}
        assert sum(day["tasks"] for day in data["per_day"]) == 5
        assert len(data["per_day"]) == 7  # quiet days are included as zeros
        assert data["per_day"][-1]["date"] == timezone.localdate().isoformat()

        assert admin_client.get(f"{BASE}/dashboard/?days=30").data["totals"]["tasks"] == 6

    def test_empty(self, admin_client):
        assert admin_client.get(f"{BASE}/dashboard/").data["totals"]["error_rate"] == 0.0


class TestUsers:
    def test_search_and_task_counts(self, admin_client):
        ali = UserFactory(email="ali@example.uz")
        UserFactory(email="bobur@example.uz")
        make_task(user=ali)
        data = admin_client.get(f"{BASE}/users/?q=ali@").data
        assert [u["email"] for u in data["results"]] == ["ali@example.uz"]
        assert data["results"][0]["tasks_30d"] == 1

    def test_block_signs_out_and_unblock_restores(self, admin_client):
        target = UserFactory()
        issue_tokens(target)
        resp = admin_client.post(f"{BASE}/users/{target.pk}/block/")
        assert resp.status_code == 200 and resp.data["is_active"] is False
        assert all(t.blacklistedtoken for t in OutstandingToken.objects.filter(user=target))
        assert admin_client.get(f"{BASE}/users/?blocked=1").data["count"] == 1
        # A blocked account can't sign in.
        login = APIClient().post(
            "/api/v1/auth/login/", {"email": target.email, "password": "Str0ng-pass-123"}, format="json"
        )
        assert login.status_code in (400, 401, 403)

        assert admin_client.delete(f"{BASE}/users/{target.pk}/block/").data["is_active"] is True

    def test_cannot_block_self_or_staff(self, admin_client, admin):
        assert admin_client.post(f"{BASE}/users/{admin.pk}/block/").data["error"]["code"] == "cannot_block_self"
        other_admin = UserFactory(is_staff=True)
        assert admin_client.post(f"{BASE}/users/{other_admin.pk}/block/").status_code == 403


class TestFailures:
    def test_metadata_only_with_summary_and_filters(self, admin_client):
        make_task(tool="pdf-merge", status="failed", code="corrupt_file")
        make_task(tool="pdf-merge", status="failed", code="corrupt_file")
        make_task(tool="office-to-pdf", status="failed", code="timeout")
        make_task(status="done")
        data = admin_client.get(f"{BASE}/failures/").data
        assert data["count"] == 3
        assert data["summary"][0] == {"tool": "pdf-merge", "error_code": "corrupt_file", "count": 2}
        assert set(data["results"][0]) == {
            "id",
            "tool",
            "source",
            "error_code",
            "created_at",
            "duration_ms",
            "input_meta",
        }
        assert admin_client.get(f"{BASE}/failures/?code=timeout").data["count"] == 1


class TestLimits:
    def test_update_and_validate(self, admin_client):
        resp = admin_client.patch(f"{BASE}/limits/guest/", {"daily_tasks": 50}, format="json")
        assert resp.status_code == 200
        assert LimitPolicy.objects.get(role="guest").daily_tasks == 50
        bad = admin_client.patch(f"{BASE}/limits/guest/", {"max_total_mb": 1, "max_file_mb": 10}, format="json")
        assert bad.status_code == 400
        assert admin_client.patch(f"{BASE}/limits/guest/", {"daily_tasks": 0}, format="json").status_code == 400
        assert admin_client.patch(f"{BASE}/limits/nobody/", {"daily_tasks": 5}, format="json").status_code == 404


class TestToolSwitch:
    def test_disabled_tool_refuses_new_tasks(self, admin_client, api_client):
        assert admin_client.patch(f"{BASE}/tools/image-convert/", {"enabled": False}, format="json").status_code == 200
        assert ToolSetting.objects.get(slug="image-convert").enabled is False
        listing = {t["slug"]: t["enabled"] for t in api_client.get("/api/v1/tools/").data}
        assert listing["image-convert"] is False and listing["pdf-merge"] is True
        resp = api_client.post(
            "/api/v1/tasks/",
            {
                "tool": "image-convert",
                "options": json.dumps({"target": "jpg"}),
                "files": [SimpleUploadedFile("a.png", make_image_bytes())],
            },
        )
        assert resp.status_code == 503 and resp.data["error"]["code"] == "tool_disabled"

    def test_validation(self, admin_client):
        assert admin_client.patch(f"{BASE}/tools/nope/", {"enabled": False}, format="json").status_code == 404
        assert admin_client.patch(f"{BASE}/tools/pdf-merge/", {"enabled": "no"}, format="json").status_code == 400


def test_load_snapshot(admin_client):
    make_task(status="queued")
    redis_client = mock.Mock(llen=mock.Mock(return_value=3))
    inspector = mock.Mock(ping=mock.Mock(return_value={"celery@w1": {"ok": "pong"}}))
    with (
        mock.patch("apps.staff.load.redis.Redis.from_url", return_value=redis_client),
        mock.patch("config.celery.app.control.inspect", return_value=inspector),
    ):
        data = admin_client.get(f"{BASE}/load/").data
    assert data["queues"] == {"light": 3, "office": 3, "maintenance": 3}
    assert data["workers"] == [{"name": "celery@w1", "ok": True}]
    assert data["tasks"]["queued"] == 1
    assert data["storage"]["disk_free"] > 0


def test_new_tasks_record_source_and_input_formats(api_client, settings):
    settings.BOT_API_SECRET = "secret-for-test"
    files = [SimpleUploadedFile("a.png", make_image_bytes())]
    payload = {"tool": "image-convert", "options": json.dumps({"target": "jpg"}), "files": files}
    web = api_client.post("/api/v1/tasks/", payload).data["id"]
    bot = APIClient(HTTP_X_BOT_SECRET="secret-for-test", HTTP_X_TELEGRAM_USER_ID="77")
    tg = bot.post("/api/v1/tasks/", {**payload, "files": [SimpleUploadedFile("b.png", make_image_bytes())]}).data["id"]
    assert Task.objects.get(pk=web).source == "web"
    task = Task.objects.get(pk=tg)
    assert task.source == "telegram"
    assert task.input_meta == [{"format": "png", "size": len(make_image_bytes())}]
