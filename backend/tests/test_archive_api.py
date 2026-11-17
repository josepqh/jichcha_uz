import json
import zipfile
from urllib.parse import unquote

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.conversions.models import LimitPolicy, Task, TaskFile
from tests.docs import rar4_bytes, zip_bytes

pytestmark = pytest.mark.django_db
URL = "/api/v1/tasks/"


def post(client, tool, files, options=None, capture=None):
    payload = {"tool": tool, "options": json.dumps(options or {}), "files": files}
    if capture is None:
        return client.post(URL, payload, format="multipart")
    with capture(execute=True):
        return client.post(URL, payload, format="multipart")


def test_tool_list_marks_any_file_tools(api_client):
    tools = {t["slug"]: t for t in api_client.get("/api/v1/tools/").data}
    assert tools["archive-create"]["accepts_any"] is True
    assert tools["archive-extract"]["accepts_any"] is False
    assert "rar" in tools["archive-extract"]["accepts"]
    assert "ebook-convert" not in tools and "text-convert" not in tools


def test_extract_rejects_non_archives(api_client, png_upload):
    assert post(api_client, "archive-extract", [png_upload()]).status_code == 415


def test_extract_end_to_end(api_client, django_capture_on_commit_callbacks):
    files = [SimpleUploadedFile("arxiv.rar", rar4_bytes({"papka/hisobot.txt": b"one", "b.txt": b"two"}))]
    task = post(api_client, "archive-extract", files, capture=django_capture_on_commit_callbacks).data
    detail = api_client.get(f"{URL}{task['id']}/").data
    assert detail["status"] == "done"
    assert [o["name"] for o in detail["outputs"]] == ["papka/hisobot.txt", "b.txt"]

    # Each file downloads under its own name (no folder), as an opaque download.
    resp = api_client.get(detail["outputs"][0]["download_url"])
    assert resp.status_code == 200
    assert resp["Content-Type"] == "application/octet-stream"
    assert "hisobot.txt" in unquote(resp["Content-Disposition"]) and "papka" not in resp["Content-Disposition"]
    assert b"".join(resp.streaming_content) == b"one"

    # No "download all" copy: the user already has the archive, and it would double the disk used.
    assert detail["bundle"] is None
    assert not TaskFile.objects.filter(task_id=task["id"], role="bundle").exists()


def test_create_accepts_any_file(api_client, django_capture_on_commit_callbacks):
    files = [SimpleUploadedFile("dastur.exe", b"MZ\x90\x00" * 10), SimpleUploadedFile("eslatma", b"\x00\x01\x02")]
    resp = post(api_client, "archive-create", files, {"format": "zip"}, django_capture_on_commit_callbacks)
    assert resp.status_code == 202
    detail = api_client.get(f"{URL}{resp.data['id']}/").data
    assert detail["status"] == "done"
    [out] = detail["outputs"]
    assert out["name"] == "archive.zip"
    stored = TaskFile.objects.get(pk=out["id"])
    with stored.file.open("rb") as fh, zipfile.ZipFile(fh) as zf:
        assert sorted(zf.namelist()) == ["dastur.exe", "eslatma"]


def test_bomb_fails_cleanly(api_client, settings, django_capture_on_commit_callbacks):
    settings.ARCHIVE_MAX_UNPACKED_MB = 1
    files = [SimpleUploadedFile("bomb.zip", zip_bytes({"zeros.bin": b"\0" * (8 * 1024 * 1024)}))]
    task = post(api_client, "archive-extract", files, capture=django_capture_on_commit_callbacks).data
    detail = api_client.get(f"{URL}{task['id']}/").data
    assert (detail["status"], detail["error_code"]) == ("failed", "archive_too_large")
    assert not TaskFile.objects.filter(task_id=task["id"]).exists()


def test_unpack_limit_follows_the_role_and_cannot_be_raised_by_the_client(api_client, settings):
    settings.ARCHIVE_MAX_UNPACKED_MB = 1024
    files = [SimpleUploadedFile("a.zip", zip_bytes({"a.txt": b"x"}))]
    resp = post(api_client, "archive-extract", files, {"_max_unpacked_mb": 999_999})
    assert resp.status_code == 202
    task = Task.objects.get(pk=resp.data["id"])
    guest_total_mb = LimitPolicy.objects.get(role="guest").max_total_mb
    assert task.options == {"_max_unpacked_mb": min(1024, guest_total_mb * 5)}
    assert resp.data["options"] == {}  # server-side limits are not echoed back


def test_repack_still_offers_one_file_per_archive(api_client, django_capture_on_commit_callbacks):
    files = [
        SimpleUploadedFile("a.rar", rar4_bytes({"x.txt": b"1"})),
        SimpleUploadedFile("b.rar", rar4_bytes({"y.txt": b"2"})),
    ]
    task = post(api_client, "archive-convert", files, {"target": "zip"}, django_capture_on_commit_callbacks).data
    detail = api_client.get(f"{URL}{task['id']}/").data
    assert [o["name"] for o in detail["outputs"]] == ["a.zip", "b.zip"]
    assert detail["bundle"] is not None
