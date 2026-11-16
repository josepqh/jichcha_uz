"""Password-protected PDFs and archives. Passwords are used for the one task and never stored."""

import json
import zipfile
from unittest import mock

import pikepdf
import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.conversions.models import Task, TaskFile
from apps.conversions.processors import archives, pdf
from apps.conversions.processors.base import InputFile, ProcessingError
from config.sentry import scrub_event
from tests.docs import encrypted_pdf_bytes, libarchive_bytes

SECRET_ZIP = {"hujjat.txt": b"maxfiy matn"}


def locked_zip() -> bytes:
    return libarchive_bytes("zip", SECRET_ZIP, passphrase="arxiv-paroli", options="encryption=zipcrypt")


def write(tmp_path, name, data, fmt):
    path = tmp_path / f"src-{name}"
    path.write_bytes(data)
    return InputFile(path, name, fmt)


class TestPdfUnlock:
    def test_right_password_gives_an_open_copy(self, tmp_path):
        src = write(tmp_path, "bayonnoma.pdf", encrypted_pdf_bytes(), "pdf")
        [out] = pdf.unlock_pdf([src], {"password": "user-pass"}, tmp_path)
        assert out.name == "bayonnoma-unlocked.pdf"
        with pikepdf.open(out.path) as doc:  # no password needed any more
            assert not doc.is_encrypted

    @pytest.mark.parametrize(("password", "code"), [("wrong", "wrong_password"), ("", "pdf_encrypted")])
    def test_wrong_or_missing_password(self, tmp_path, password, code):
        src = write(tmp_path, "a.pdf", encrypted_pdf_bytes(), "pdf")
        with pytest.raises(ProcessingError) as exc:
            pdf.unlock_pdf([src], {"password": password}, tmp_path)
        assert exc.value.code == code


class TestArchivePassword:
    def test_extract_with_the_password(self, tmp_path):
        src = write(tmp_path, "a.zip", locked_zip(), "zip")
        files = archives.extract(  # noqa: F841 - names checked below
            [src], {"password": "arxiv-paroli"}, tmp_path
        )
        assert {f.name: f.path.read_bytes() for f in files} == SECRET_ZIP

    @pytest.mark.parametrize(("password", "code"), [("nope", "wrong_password"), ("", "archive_encrypted")])
    def test_wrong_or_missing_password(self, tmp_path, password, code):
        src = write(tmp_path, "a.zip", locked_zip(), "zip")
        with pytest.raises(ProcessingError) as exc:
            archives.extract([src], {"password": password}, tmp_path)
        assert exc.value.code == code

    def test_repack_with_password(self, tmp_path):
        src = write(tmp_path, "a.zip", locked_zip(), "zip")
        [out] = archives.repack([src], {"target": "zip", "password": "arxiv-paroli"}, tmp_path)
        with zipfile.ZipFile(out.path) as zf:  # the new zip has no password
            assert zf.read("hujjat.txt") == b"maxfiy matn"


@pytest.mark.django_db
class TestNeverStored:
    def post(self, client, tool, name, data, options, capture):
        payload = {"tool": tool, "options": json.dumps(options), "files": [SimpleUploadedFile(name, data)]}
        with capture(execute=True):
            return client.post("/api/v1/tasks/", payload)

    def test_password_reaches_the_worker_but_not_the_database(self, api_client, django_capture_on_commit_callbacks):
        from apps.conversions import tasks

        with mock.patch.object(tasks.run_conversion, "apply_async", wraps=tasks.run_conversion.apply_async) as spy:
            resp = self.post(
                api_client,
                "pdf-unlock",
                "a.pdf",
                encrypted_pdf_bytes(),
                {"password": "user-pass"},
                django_capture_on_commit_callbacks,
            )
        assert resp.status_code == 202
        assert "password" not in json.dumps(resp.data)
        task = Task.objects.get(pk=resp.data["id"])
        assert "password" not in task.options
        assert spy.call_args.kwargs["kwargs"] == {"secrets": {"password": "user-pass"}}
        assert task.status == "done"
        assert TaskFile.objects.filter(task=task, role="output").exists()

    def test_archive_password_end_to_end(self, api_client, django_capture_on_commit_callbacks):
        resp = self.post(
            api_client,
            "archive-extract",
            "a.zip",
            locked_zip(),
            {"password": "arxiv-paroli"},
            django_capture_on_commit_callbacks,
        )
        task = Task.objects.get(pk=resp.data["id"])
        assert (task.status, task.options.get("password")) == ("done", None)

    def test_unlock_requires_a_password(self, api_client):
        payload = {"tool": "pdf-unlock", "options": "{}", "files": [SimpleUploadedFile("a.pdf", encrypted_pdf_bytes())]}
        assert api_client.post("/api/v1/tasks/", payload).status_code == 400


def test_sentry_drops_celery_job_arguments():
    event = {"extra": {"celery-job": {"kwargs": {"secrets": {"password": "x"}}}}, "contexts": {"celery-job": {}}}
    assert scrub_event(event, None) == {"contexts": {}}
