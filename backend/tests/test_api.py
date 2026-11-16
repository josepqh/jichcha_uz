import json
from datetime import timedelta
from pathlib import Path

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone
from rest_framework.test import APIClient

from apps.conversions import services
from apps.conversions.downloads import signed_download_url
from apps.conversions.models import LimitPolicy, Task, TaskFile, UsageCounter
from tests.conftest import make_image_bytes
from tests.factories import UserFactory

pytestmark = pytest.mark.django_db

TASKS_URL = "/api/v1/tasks/"


def post_task(client, files, tool="image-convert", options=None, capture=None):
    payload = {
        "tool": tool,
        "options": json.dumps(options if options is not None else {"target": "jpg"}),
        "files": files,
    }
    if capture is None:
        return client.post(TASKS_URL, payload, format="multipart")
    with capture(execute=True):
        return client.post(TASKS_URL, payload, format="multipart")


@pytest.fixture
def run_tasks(django_capture_on_commit_callbacks):
    """Runs the Celery task (eager) when the request's transaction commits."""
    return django_capture_on_commit_callbacks


class TestGuestFlow:
    def test_convert_png_to_jpg_end_to_end(self, api_client, png_upload, run_tasks, media_root):
        resp = post_task(api_client, [png_upload("rasm.png")], capture=run_tasks)

        assert resp.status_code == 202
        assert "uv_guest" in resp.cookies
        assert resp.cookies["uv_guest"]["httponly"]
        task_id = resp.data["id"]

        detail = api_client.get(f"{TASKS_URL}{task_id}/")
        assert detail.status_code == 200
        assert detail.data["status"] == "done"
        [output] = detail.data["outputs"]
        assert output["name"] == "rasm.jpg"
        assert detail.data["bundle"] is None

        download = api_client.get(output["download_url"])
        assert download.status_code == 200
        assert download["Content-Type"] == "image/jpeg"
        assert 'attachment; filename="rasm.jpg"' in download["Content-Disposition"]
        assert b"".join(download.streaming_content)[:2] == b"\xff\xd8"

        # Inputs are deleted right after processing.
        assert not TaskFile.objects.filter(task_id=task_id, role="input").exists()
        assert not list(Path(media_root).glob(f"tasks/{task_id}/input/*"))

    def test_multiple_outputs_get_a_zip_bundle(self, api_client, png_upload, run_tasks):
        resp = post_task(api_client, [png_upload("a.png"), png_upload("a.png")], capture=run_tasks)
        detail = api_client.get(f"{TASKS_URL}{resp.data['id']}/").data
        assert [o["name"] for o in detail["outputs"]] == ["a.jpg", "a (2).jpg"]
        assert detail["bundle"]["name"] == "universe-image-convert.zip"

    def test_images_to_pdf(self, api_client, png_upload, run_tasks):
        resp = post_task(
            api_client,
            [png_upload("1.png"), png_upload("2.png")],
            tool="images-to-pdf",
            options={"page_size": "a4"},
            capture=run_tasks,
        )
        detail = api_client.get(f"{TASKS_URL}{resp.data['id']}/").data
        assert detail["status"] == "done"
        assert detail["options"] == {"page_size": "a4", "orientation": "auto", "margin": "small"}
        assert [o["mime"] for o in detail["outputs"]] == ["application/pdf"]

    def test_corrupt_image_fails_with_code(self, api_client, run_tasks):
        broken = SimpleUploadedFile("x.png", make_image_bytes("PNG")[:70])
        resp = post_task(api_client, [broken], capture=run_tasks)
        detail = api_client.get(f"{TASKS_URL}{resp.data['id']}/").data
        assert detail["status"] == "failed"
        assert detail["error_code"] == "corrupt_file"
        assert detail["outputs"] == []

    def test_delete_now_removes_files(self, api_client, png_upload, run_tasks, media_root):
        resp = post_task(api_client, [png_upload()], capture=run_tasks)
        task_id = resp.data["id"]
        url = api_client.get(f"{TASKS_URL}{task_id}/").data["outputs"][0]["download_url"]

        assert api_client.delete(f"{TASKS_URL}{task_id}/").status_code == 204

        assert api_client.get(url).status_code == 404
        assert api_client.get(f"{TASKS_URL}{task_id}/").data["files_deleted"] is True
        assert not list(Path(media_root).glob(f"tasks/{task_id}/**/*.*"))


class TestOwnership:
    def test_other_guest_cannot_see_or_delete(self, api_client, png_upload, run_tasks):
        task_id = post_task(api_client, [png_upload()], capture=run_tasks).data["id"]

        stranger = APIClient()
        post_task(stranger, [png_upload()])  # stranger has their own guest cookie
        assert stranger.get(f"{TASKS_URL}{task_id}/").status_code == 404
        assert stranger.delete(f"{TASKS_URL}{task_id}/").status_code == 404

    def test_client_without_cookie_gets_404(self, api_client, png_upload):
        task_id = post_task(api_client, [png_upload()]).data["id"]
        assert APIClient().get(f"{TASKS_URL}{task_id}/").status_code == 404

    def test_forged_cookie_is_ignored(self, api_client, png_upload):
        task_id = post_task(api_client, [png_upload()]).data["id"]
        forger = APIClient()
        forger.cookies["uv_guest"] = "forged-value"
        assert forger.get(f"{TASKS_URL}{task_id}/").status_code == 404

    def test_user_cannot_access_guest_or_other_user_task(self, api_client, user_client, png_upload):
        guest_task = post_task(api_client, [png_upload()]).data["id"]
        other = APIClient()
        other.force_authenticate(UserFactory())
        other_task = post_task(other, [png_upload()]).data["id"]

        assert user_client.get(f"{TASKS_URL}{guest_task}/").status_code == 404
        assert user_client.get(f"{TASKS_URL}{other_task}/").status_code == 404

    def test_guest_task_stays_visible_after_signing_in_same_browser(self, api_client, png_upload, user):
        task_id = post_task(api_client, [png_upload()]).data["id"]
        api_client.force_authenticate(user)  # same client, same guest cookie
        assert api_client.get(f"{TASKS_URL}{task_id}/").status_code == 200

        other_browser = APIClient()
        other_browser.force_authenticate(user)  # same account, no guest cookie
        assert other_browser.get(f"{TASKS_URL}{task_id}/").status_code == 404

    def test_input_files_are_never_downloadable(self, api_client, png_upload):
        task_id = post_task(api_client, [png_upload()]).data["id"]  # not processed: input still exists
        input_file = TaskFile.objects.select_related("task").get(task_id=task_id, role="input")
        url = signed_download_url(input_file.pk, input_file.task.expires_at)  # even with a valid signature
        assert api_client.get(url).status_code == 404


class TestSignedDownloads:
    @pytest.fixture
    def output(self, api_client, png_upload, run_tasks):
        task_id = post_task(api_client, [png_upload()], capture=run_tasks).data["id"]
        return api_client.get(f"{TASKS_URL}{task_id}/").data["outputs"][0]

    def test_link_works_without_cookie_or_token(self, output):
        assert APIClient().get(output["download_url"]).status_code == 200

    def test_tampered_signature_rejected(self, output):
        assert APIClient().get(output["download_url"][:-3] + "abc").status_code == 404

    def test_missing_token_rejected(self, output):
        assert APIClient().get(f"/api/v1/files/{output['id']}/").status_code == 404

    def test_token_for_one_file_does_not_open_another(self, api_client, output, png_upload, run_tasks):
        other_task = post_task(api_client, [png_upload()], capture=run_tasks).data["id"]
        other_id = api_client.get(f"{TASKS_URL}{other_task}/").data["outputs"][0]["id"]
        token = output["download_url"].split("?t=")[1]
        assert APIClient().get(f"/api/v1/files/{other_id}/?t={token}").status_code == 404

    def test_expired_token_rejected(self, output):
        expired = signed_download_url(output["id"], timezone.now() - timedelta(seconds=1))
        assert APIClient().get(expired).status_code == 404

    def test_registered_user_can_download_own_output(self, user_client, png_upload, run_tasks):
        task_id = post_task(user_client, [png_upload()], capture=run_tasks).data["id"]
        url = user_client.get(f"{TASKS_URL}{task_id}/").data["outputs"][0]["download_url"]
        assert APIClient().get(url).status_code == 200


class TestValidation:
    def test_fake_png_is_rejected_by_content(self, api_client):
        fake = SimpleUploadedFile("evil.png", b"<html><script>alert(1)</script></html>", content_type="image/png")
        resp = post_task(api_client, [fake])
        assert resp.status_code == 415
        assert resp.data["error"]["code"] == "unsupported_format"
        assert Task.objects.count() == 0

    def test_unknown_tool(self, api_client, png_upload):
        resp = post_task(api_client, [png_upload()], tool="rm-rf")
        assert resp.status_code == 400
        assert resp.data["error"]["code"] == "unknown_tool"

    def test_invalid_option_value(self, api_client, png_upload):
        resp = post_task(api_client, [png_upload()], options={"target": "exe"})
        assert resp.status_code == 400
        assert resp.data["error"]["code"] == "validation_error"
        assert "target" in resp.data["error"]["details"]

    def test_no_files(self, api_client):
        resp = post_task(api_client, [])
        assert resp.status_code == 400
        assert resp.data["error"]["code"] == "no_files"

    def test_too_many_files_for_guest(self, api_client, png_upload):
        resp = post_task(api_client, [png_upload(f"{i}.png") for i in range(11)])
        assert resp.status_code == 400
        assert resp.data["error"] == {
            "code": "too_many_files",
            "message": "Too many files.",
            "details": {"max_files": 10},
        }

    def test_registered_user_has_bigger_batch(self, user_client, png_upload):
        resp = post_task(user_client, [png_upload(f"{i}.png") for i in range(11)])
        assert resp.status_code == 202

    def test_file_too_large(self, api_client):
        LimitPolicy.objects.filter(role="guest").update(max_file_mb=1)
        big = SimpleUploadedFile("big.bmp", make_image_bytes("BMP", size=(700, 700), mode="RGB"))
        resp = post_task(api_client, [big])
        assert resp.status_code == 413
        assert resp.data["error"]["code"] == "file_too_large"

    def test_content_length_checked_before_parsing(self, api_client):
        LimitPolicy.objects.filter(role="guest").update(max_file_mb=1, max_total_mb=1)
        resp = api_client.post(
            TASKS_URL, data=b"x", content_type="multipart/form-data; boundary=x", CONTENT_LENGTH=str(5 * 1024 * 1024)
        )
        assert resp.status_code == 413
        assert resp.data["error"]["code"] == "request_too_large"

    def test_daily_limit(self, api_client, png_upload):
        LimitPolicy.objects.filter(role="guest").update(daily_tasks=2)
        assert post_task(api_client, [png_upload()]).status_code == 202
        assert post_task(api_client, [png_upload()]).status_code == 202
        resp = post_task(api_client, [png_upload()])
        assert resp.status_code == 429
        assert resp.data["error"]["code"] == "daily_limit_reached"
        assert Task.objects.count() == 2

    def test_rejected_request_does_not_consume_quota(self, api_client):
        post_task(api_client, [SimpleUploadedFile("x.png", b"nope")])
        assert UsageCounter.objects.count() == 0


class TestUsageAndTools:
    def test_tools_listing(self, api_client):
        slugs = {t["slug"] for t in api_client.get("/api/v1/tools/").data}
        assert slugs == {
            "image-convert",
            "image-compress",
            "images-to-pdf",
            "office-to-pdf",
            "pdf-merge",
            "pdf-split",
            "pdf-organize",
            "pdf-compress",
            "pdf-to-images",
            "archive-extract",
            "archive-create",
            "archive-convert",
            "ebook-convert",
            "image-edit",
            "text-convert",
        }

    def test_usage_counts_today(self, api_client, png_upload):
        assert api_client.get("/api/v1/usage/").data["today"]["tasks_used"] == 0
        post_task(api_client, [png_upload()])
        data = api_client.get("/api/v1/usage/").data
        assert data["role"] == "guest"
        assert data["today"] == {"tasks_used": 1, "tasks_left": 19}

    def test_history_requires_account(self, api_client, user_client, png_upload):
        assert api_client.get(f"{TASKS_URL}history/").status_code == 401
        post_task(user_client, [png_upload()])
        assert user_client.get(f"{TASKS_URL}history/").data["count"] == 1


class TestPurge:
    def test_expired_files_are_purged(self, api_client, png_upload, run_tasks, media_root):
        task_id = post_task(api_client, [png_upload()], capture=run_tasks).data["id"]
        Task.objects.filter(pk=task_id).update(expires_at=timezone.now() - timedelta(minutes=1))

        assert services.purge_expired() == 1

        task = Task.objects.get(pk=task_id)
        assert task.files_purged_at is not None
        assert not task.files.exists()
        assert not list(Path(media_root).glob(f"tasks/{task_id}/**/*.*"))

    def test_stuck_tasks_marked_failed(self, api_client, png_upload):
        task_id = post_task(api_client, [png_upload()]).data["id"]
        Task.objects.filter(pk=task_id).update(created_at=timezone.now() - timedelta(hours=1))
        services.purge_expired()
        task = Task.objects.get(pk=task_id)
        assert (task.status, task.error_code) == ("failed", "timeout")

    def test_old_history_deleted(self, api_client, png_upload):
        task_id = post_task(api_client, [png_upload()]).data["id"]
        Task.objects.filter(pk=task_id).update(created_at=timezone.now() - timedelta(days=31))
        services.purge_expired()
        assert not Task.objects.filter(pk=task_id).exists()

    def test_reprocessing_is_a_no_op(self, api_client, png_upload, run_tasks, tmp_path):
        task_id = post_task(api_client, [png_upload()], capture=run_tasks).data["id"]
        services.process_task(task_id, tmp_path)  # duplicate delivery (acks_late)
        assert TaskFile.objects.filter(task_id=task_id, role="output").count() == 1


class TestThrottleIdentity:
    def test_client_ip_comes_from_last_forwarded_hop(self, settings, rf):
        from rest_framework.request import Request
        from rest_framework.throttling import AnonRateThrottle

        settings.REST_FRAMEWORK = {**settings.REST_FRAMEWORK, "NUM_PROXIES": 1}
        from rest_framework import settings as drf_settings

        drf_settings.api_settings.reload()
        try:
            spoofed = rf.get("/", HTTP_X_FORWARDED_FOR="1.1.1.1, 203.0.113.7", REMOTE_ADDR="172.18.0.5")
            assert AnonRateThrottle().get_ident(Request(spoofed)) == "203.0.113.7"
        finally:
            drf_settings.api_settings.reload()


class TestTaskCreateThrottle:
    """The per-minute limit follows the account or guest browser, not the shared IP (CGNAT)."""

    @pytest.fixture
    def rates(self):
        from unittest import mock

        from apps.conversions.throttles import (
            AnonIPRateThrottle,
            GuestRateThrottle,
            GuestTaskCreateIPThrottle,
            TaskCreateThrottle,
        )

        def apply(per_identity: str, per_ip: str, anon: str = "1000/min", anon_ip: str = "1000/min"):
            rates = {"task_create": per_identity, "task_create_ip": per_ip, "anon": anon, "anon_ip": anon_ip}
            # DRF snapshots throttle rates into a class attribute at import time.
            for cls in (TaskCreateThrottle, GuestTaskCreateIPThrottle, GuestRateThrottle, AnonIPRateThrottle):
                stack.enter_context(mock.patch.object(cls, "THROTTLE_RATES", rates))

        from contextlib import ExitStack

        with ExitStack() as stack:
            yield apply

    def test_guests_behind_one_ip_have_their_own_limits(self, db, rates, png_upload):
        rates("2/min", "100/min")
        alice, bob = APIClient(), APIClient()
        assert [post_task(alice, [png_upload()]).status_code for _ in range(4)] == [202, 202, 202, 429]
        assert [post_task(bob, [png_upload()]).status_code for _ in range(3)] == [202, 202, 202]

    def test_new_guests_behind_one_ip_are_not_throttled_together(self, db, rates, png_upload):
        rates("1/min", "100/min")
        codes = [post_task(APIClient(), [png_upload()]).status_code for _ in range(5)]
        assert codes == [202] * 5

    def test_ip_ceiling_still_caps_guests_who_clear_cookies(self, db, rates, png_upload):
        rates("100/min", "3/min")
        codes = [post_task(APIClient(), [png_upload()]).status_code for _ in range(4)]  # fresh cookie each time
        assert codes == [202, 202, 202, 429]

    def test_signed_in_users_ignore_the_guest_ip_ceiling(self, user_client, rates, png_upload):
        rates("3/min", "1/min")
        codes = [post_task(user_client, [png_upload()]).status_code for _ in range(4)]
        assert codes == [202, 202, 202, 429]


class TestHealth:
    def test_ok(self, db, api_client, settings):
        settings.HEALTH_MIN_FREE_MB = 0  # don't depend on the test machine's disk
        resp = api_client.get("/api/v1/health/")
        assert resp.status_code == 200
        assert resp.data == {"status": "ok", "checks": {"database": True, "cache": True, "disk": True}}

    def test_low_disk_fails(self, db, api_client, settings):
        settings.HEALTH_MIN_FREE_MB = 10**12  # more than any disk
        resp = api_client.get("/api/v1/health/")
        assert resp.status_code == 503
        assert resp.data["checks"]["disk"] is False


def test_sentry_scrubber_drops_tokens_and_identity():
    from config.sentry import scrub_event

    event = {
        "request": {
            "url": "https://x/api/v1/files/1/",
            "query_string": "t=signed",
            "cookies": {"a": "b"},
            "headers": {},
        },
        "user": {"ip_address": "1.2.3.4"},
    }
    assert scrub_event(event, None) == {"request": {"url": "https://x/api/v1/files/1/"}}


class TestGeneralGuestThrottle:
    """Status polling (GET) is limited per guest browser, so people behind one IP don't block each other."""

    @pytest.fixture
    def rates(self):
        from contextlib import ExitStack
        from unittest import mock

        from apps.conversions.throttles import AnonIPRateThrottle, GuestRateThrottle

        with ExitStack() as stack:

            def apply(anon: str, anon_ip: str):
                rates = {"anon": anon, "anon_ip": anon_ip}
                for cls in (GuestRateThrottle, AnonIPRateThrottle):
                    stack.enter_context(mock.patch.object(cls, "THROTTLE_RATES", rates))

            yield apply

    def test_two_guests_on_one_ip_poll_independently(self, db, rates, png_upload):
        rates("3/min", "100/min")
        alice, bob = APIClient(), APIClient()
        for client in (alice, bob):
            post_task(client, [png_upload()])  # first request (no cookie yet) counts against the IP
        assert [alice.get("/api/v1/usage/").status_code for _ in range(4)] == [200, 200, 200, 429]
        assert [bob.get("/api/v1/usage/").status_code for _ in range(3)] == [200, 200, 200]

    def test_ip_ceiling_applies_to_all_guests_together(self, db, rates):
        rates("100/min", "3/min")
        codes = [APIClient().get("/api/v1/usage/").status_code for _ in range(4)]  # four "different" guests
        assert codes == [200, 200, 200, 429]

    def test_signed_in_users_are_not_counted_as_guests(self, user_client, rates):
        rates("1/min", "1/min")
        assert [user_client.get("/api/v1/usage/").status_code for _ in range(3)] == [200, 200, 200]


def test_user_rate_does_not_cap_guests_by_ip(db, settings):
    """The per-user limit must not fall back to one shared per-IP bucket for guests (CGNAT)."""
    from unittest import mock

    from apps.conversions.throttles import AnonIPRateThrottle, GuestRateThrottle, SignedInUserRateThrottle

    rates = {"user": "2/min", "anon": "100/min", "anon_ip": "100/min"}
    with (
        mock.patch.object(SignedInUserRateThrottle, "THROTTLE_RATES", rates),
        mock.patch.object(GuestRateThrottle, "THROTTLE_RATES", rates),
        mock.patch.object(AnonIPRateThrottle, "THROTTLE_RATES", rates),
    ):
        codes = [APIClient().get("/api/v1/usage/").status_code for _ in range(5)]
    assert codes == [200] * 5


def test_missing_task_has_the_not_found_code(db, api_client):
    resp = api_client.get("/api/v1/tasks/01a1e5a8-0000-7000-8000-000000000000/")
    assert resp.status_code == 404
    assert resp.data["error"]["code"] == "not_found"
