"""PDF page tools: each one checked on the real output file."""

import json

import pikepdf
import pypdfium2 as pdfium
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.conversions.models import Task
from apps.conversions.processors import pdf_edit
from apps.conversions.processors.base import InputFile, ProcessingError
from tests.docs import pdf_bytes


def write(tmp_path, data, name="doc.pdf"):
    path = tmp_path / f"src-{name}"
    path.write_bytes(data)
    return InputFile(path=path, name=name, fmt="pdf")


def text_of(path) -> list[str]:
    doc = pdfium.PdfDocument(path)
    try:
        return [doc[i].get_textpage().get_text_range() for i in range(len(doc))]
    finally:
        doc.close()


def test_rotate_every_page(tmp_path):
    [out] = pdf_edit.rotate_pdf([write(tmp_path, pdf_bytes(2))], {"angle": "90"}, tmp_path)
    assert out.name == "doc-rotated.pdf"
    with pikepdf.open(out.path) as doc:
        assert [int(p.obj.get("/Rotate", 0)) for p in doc.pages] == [90, 90]


def test_remove_and_extract_pages(tmp_path):
    src = write(tmp_path, pdf_bytes(5))
    [removed] = pdf_edit.remove_pages([src], {"pages": "2, 4-5"}, tmp_path)
    [extracted] = pdf_edit.extract_pages([src], {"pages": "5, 1-2, 2"}, tmp_path)
    with pikepdf.open(removed.path) as a, pikepdf.open(extracted.path) as b:
        assert len(a.pages) == 2
        assert len(b.pages) == 3  # 1, 2 and 5 in document order, each once
    with pytest.raises(ProcessingError) as exc:
        pdf_edit.remove_pages([src], {"pages": "1-5"}, tmp_path)
    assert exc.value.code == "all_pages_removed"


def test_page_numbers(tmp_path):
    src = write(tmp_path, pdf_bytes(3))
    [out] = pdf_edit.add_page_numbers([src], {"position": "bottom-right", "start": 1, "style": "n-of-total"}, tmp_path)
    texts = text_of(out.path)
    assert [t.strip() for t in texts] == ["1 / 3", "2 / 3", "3 / 3"]


def test_watermark_keeps_non_latin_text(tmp_path):
    [out] = pdf_edit.add_watermark(
        [write(tmp_path, pdf_bytes(1))], {"text": "Maxfiy — Секретно oʻgʻ", "opacity": "medium"}, tmp_path
    )
    assert "Секретно" in text_of(out.path)[0]


def test_crop_sets_the_crop_box(tmp_path):
    [out] = pdf_edit.crop_pdf([write(tmp_path, pdf_bytes(1, size=(800, 600)))], {"margin": "10"}, tmp_path)
    with pikepdf.open(out.path) as doc:
        media = [float(v) for v in doc.pages[0].mediabox]
        crop = [float(v) for v in doc.pages[0].obj.CropBox]
    margin = 10 * 72 / 25.4
    assert crop == pytest.approx([media[0] + margin, media[1] + margin, media[2] - margin, media[3] - margin])


def test_crop_refuses_to_eat_the_page(tmp_path):
    with pytest.raises(ProcessingError) as exc:
        pdf_edit.crop_pdf([write(tmp_path, pdf_bytes(1, size=(60, 60)))], {"margin": "25"}, tmp_path)
    assert exc.value.code == "crop_too_large"


def test_protect_then_only_the_password_opens_it(tmp_path):
    [out] = pdf_edit.protect_pdf([write(tmp_path, pdf_bytes(1))], {"password": "s3cret-pass"}, tmp_path)
    with pytest.raises(pikepdf.PasswordError):
        pikepdf.open(out.path)
    with pikepdf.open(out.path, password="s3cret-pass") as doc:
        assert doc.is_encrypted and len(doc.pages) == 1


def test_repair_rebuilds_a_broken_xref(tmp_path):
    data = pdf_bytes(2)
    broken = data[: data.rfind(b"xref")] + b"%%EOF\n"  # cross-reference table cut off
    [out] = pdf_edit.repair_pdf([write(tmp_path, broken)], {}, tmp_path)
    with pikepdf.open(out.path) as doc:
        assert len(doc.pages) == 2


@pytest.mark.django_db
class TestThroughTheApi:
    def post(self, client, tool, options, capture, data=None):
        upload = SimpleUploadedFile("a.pdf", data or pdf_bytes(3))
        payload = {"tool": tool, "options": json.dumps(options), "files": [upload]}
        with capture(execute=True):
            return client.post("/api/v1/tasks/", payload)

    def test_protect_password_is_not_stored(self, api_client, django_capture_on_commit_callbacks):
        resp = self.post(api_client, "pdf-protect", {"password": "s3cret-pass"}, django_capture_on_commit_callbacks)
        assert resp.status_code == 202
        task = Task.objects.get(pk=resp.data["id"])
        assert (task.status, "password" in task.options) == ("done", False)

    @pytest.mark.parametrize(
        ("tool", "options"),
        [
            ("pdf-remove-pages", {"pages": "1-x"}),
            ("pdf-watermark", {"text": ""}),
            ("pdf-protect", {"password": "abc"}),
            ("pdf-crop", {"margin": "99"}),
        ],
    )
    def test_bad_options(self, api_client, tool, options):
        payload = {"tool": tool, "options": json.dumps(options), "files": [SimpleUploadedFile("a.pdf", pdf_bytes(1))]}
        assert api_client.post("/api/v1/tasks/", payload).status_code == 400

    def test_scan_to_pdf_takes_photos(self, api_client, django_capture_on_commit_callbacks, png_upload):
        payload = {"tool": "scan-to-pdf", "options": "{}", "files": [png_upload("page1.png"), png_upload("page2.png")]}
        with django_capture_on_commit_callbacks(execute=True):
            resp = api_client.post("/api/v1/tasks/", payload)
        task = Task.objects.get(pk=resp.data["id"])
        assert task.status == "done"
