import json

import pikepdf
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.conversions.models import TaskFile
from tests.docs import docx_bytes, pdf_bytes

pytestmark = pytest.mark.django_db
URL = "/api/v1/tasks/"


def upload(name: str, data: bytes) -> SimpleUploadedFile:
    return SimpleUploadedFile(name, data)


def post(client, tool, files, options=None, capture=None):
    payload = {"tool": tool, "options": json.dumps(options or {}), "files": files}
    if capture is None:
        return client.post(URL, payload, format="multipart")
    with capture(execute=True):
        return client.post(URL, payload, format="multipart")


def test_merge_needs_two_files(api_client):
    resp = post(api_client, "pdf-merge", [upload("a.pdf", pdf_bytes(1))])
    assert resp.status_code == 400
    assert resp.data["error"] == {"code": "too_few_files", "message": "Select more files.", "details": {"min_files": 2}}


def test_merge_end_to_end(api_client, django_capture_on_commit_callbacks):
    files = [upload("a.pdf", pdf_bytes(2)), upload("b.pdf", pdf_bytes(1))]
    task = post(api_client, "pdf-merge", files, capture=django_capture_on_commit_callbacks).data
    detail = api_client.get(f"{URL}{task['id']}/").data
    assert detail["status"] == "done"
    [out] = detail["outputs"]
    assert out["name"] == "a-merged.pdf"
    stored = TaskFile.objects.get(pk=out["id"])
    with stored.file.open("rb") as fh, pikepdf.open(fh) as doc:
        assert len(doc.pages) == 3


def test_image_tool_rejects_pdf_and_pdf_tool_rejects_image(api_client, png_upload):
    assert post(api_client, "image-convert", [upload("x.pdf", pdf_bytes(1))], {"target": "jpg"}).status_code == 415
    assert post(api_client, "pdf-compress", [png_upload()]).status_code == 415


def test_office_tool_accepts_docx_by_content(api_client):
    resp = post(api_client, "office-to-pdf", [upload("referat.docx", docx_bytes())])
    assert resp.status_code == 202
    stored = TaskFile.objects.get(task_id=resp.data["id"], role="input")
    assert stored.mime_type == "application/vnd.openxmlformats-officedocument.wordprocessingml.document"
    assert stored.file.name.endswith(".docx")


def test_single_file_tools_refuse_batches(api_client):
    resp = post(api_client, "pdf-split", [upload("a.pdf", pdf_bytes(1)), upload("b.pdf", pdf_bytes(1))])
    assert resp.data["error"]["code"] == "too_many_files"
    assert resp.data["error"]["details"] == {"max_files": 1}


@pytest.mark.parametrize(
    "options",
    [
        {"mode": "ranges", "ranges": "1-3; rm -rf"},
        {"mode": "ranges"},
    ],
)
def test_split_validates_ranges(api_client, options):
    resp = post(api_client, "pdf-split", [upload("a.pdf", pdf_bytes(1))], options)
    assert resp.status_code == 400
    assert "ranges" in resp.data["error"]["details"]


@pytest.mark.parametrize(
    "options",
    [{}, {"pages": []}, {"pages": [{"page": 0}]}, {"pages": [{"page": 1, "rotate": 45}]}],
)
def test_organize_validates_pages(api_client, options):
    resp = post(api_client, "pdf-organize", [upload("a.pdf", pdf_bytes(1))], options)
    assert resp.status_code == 400


def test_organize_out_of_range_page_fails_task(api_client, django_capture_on_commit_callbacks):
    task = post(
        api_client,
        "pdf-organize",
        [upload("a.pdf", pdf_bytes(2))],
        {"pages": [{"page": 7}]},
        capture=django_capture_on_commit_callbacks,
    ).data
    detail = api_client.get(f"{URL}{task['id']}/").data
    assert (detail["status"], detail["error_code"]) == ("failed", "invalid_page_range")


def test_pdf_to_images_bundles_pages(api_client, django_capture_on_commit_callbacks):
    task = post(
        api_client,
        "pdf-to-images",
        [upload("slayd.pdf", pdf_bytes(3))],
        {"format": "png", "quality": "low"},
        capture=django_capture_on_commit_callbacks,
    ).data
    detail = api_client.get(f"{URL}{task['id']}/").data
    assert [o["name"] for o in detail["outputs"]] == ["slayd-001.png", "slayd-002.png", "slayd-003.png"]
    assert detail["bundle"]["name"] == "universe-pdf-to-images.zip"
