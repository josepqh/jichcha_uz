import json
import socket
import struct
import threading

import pytest
from django.core.files.uploadedfile import SimpleUploadedFile

from apps.conversions import antivirus
from apps.conversions.models import TaskFile
from tests.docs import zip_bytes

# The industry-standard harmless test string every antivirus detects.
EICAR = rb"X5O!P%@AP[4\PZX54(P^)7CC)7}$EICAR-STANDARD-ANTIVIRUS-TEST-FILE!$H+H*"


class FakeClamd:
    """Speaks just enough of clamd's INSTREAM protocol: FOUND when the stream contains EICAR."""

    def __init__(self, reply: bytes | None = None):
        self.reply = reply
        self.sock = socket.socket()
        self.sock.bind(("127.0.0.1", 0))
        self.sock.listen()
        self.port = self.sock.getsockname()[1]
        self.received = b""
        threading.Thread(target=self._serve, daemon=True).start()

    def _read(self, conn, n: int) -> bytes:
        data = b""
        while len(data) < n:
            chunk = conn.recv(n - len(data))
            if not chunk:
                raise ConnectionError
            data += chunk
        return data

    def _serve(self):
        while True:
            try:
                conn, _ = self.sock.accept()
            except OSError:
                return
            with conn:
                assert self._read(conn, 10) == b"zINSTREAM\0"
                stream = b""
                while size := struct.unpack("!I", self._read(conn, 4))[0]:
                    stream += self._read(conn, size)
                self.received = stream
                if self.reply is not None:
                    conn.sendall(self.reply)
                elif EICAR in stream:
                    conn.sendall(b"stream: Eicar-Test-Signature FOUND\0")
                else:
                    conn.sendall(b"stream: OK\0")

    def close(self):
        self.sock.close()


@pytest.fixture
def clamd(settings):
    server = FakeClamd()
    settings.CLAMAV_HOST, settings.CLAMAV_PORT, settings.CLAMAV_TIMEOUT = "127.0.0.1", server.port, 5
    yield server
    server.close()


def test_clean_and_infected(clamd, tmp_path):
    clean = tmp_path / "clean.bin"
    clean.write_bytes(b"a" * 200_000)  # several chunks
    assert antivirus.scan_file(clean) is None
    assert clamd.received == b"a" * 200_000
    bad = tmp_path / "bad.txt"
    bad.write_bytes(EICAR)
    assert antivirus.scan_file(bad) == "Eicar-Test-Signature"


def test_unexpected_reply_and_unreachable(settings, tmp_path):
    f = tmp_path / "x"
    f.write_bytes(b"x")
    server = FakeClamd(reply=b"INSTREAM size limit exceeded. ERROR\0")
    settings.CLAMAV_HOST, settings.CLAMAV_PORT, settings.CLAMAV_TIMEOUT = "127.0.0.1", server.port, 5
    with pytest.raises(antivirus.ScanUnavailableError):
        antivirus.scan_file(f)
    server.close()
    with pytest.raises(antivirus.ScanUnavailableError):
        antivirus.scan_file(f)


def post(client, tool, files, capture, options=None):
    payload = {"tool": tool, "options": json.dumps(options or {}), "files": files}
    with capture(execute=True):
        return client.post("/api/v1/tasks/", payload, format="multipart")


@pytest.mark.django_db
def test_infected_upload_is_rejected_before_processing(clamd, api_client, django_capture_on_commit_callbacks):
    # EICAR inside a zip: a real clamd unpacks archives; the fake one sees the stored bytes.
    files = [SimpleUploadedFile("hujjatlar.zip", zip_bytes({"virus.txt": EICAR}, compression=0))]
    task = post(api_client, "archive-extract", files, django_capture_on_commit_callbacks).data
    detail = api_client.get(f"/api/v1/tasks/{task['id']}/").data
    assert (detail["status"], detail["error_code"]) == ("failed", "malware_detected")
    assert not TaskFile.objects.filter(task_id=task["id"]).exists()


@pytest.mark.django_db
def test_scanner_down_fails_closed(settings, api_client, django_capture_on_commit_callbacks):
    settings.CLAMAV_HOST, settings.CLAMAV_PORT, settings.CLAMAV_TIMEOUT = "127.0.0.1", 1, 2
    files = [SimpleUploadedFile("a.zip", zip_bytes({"a.txt": b"x"}))]
    task = post(api_client, "archive-extract", files, django_capture_on_commit_callbacks).data
    detail = api_client.get(f"/api/v1/tasks/{task['id']}/").data
    assert (detail["status"], detail["error_code"]) == ("failed", "scan_unavailable")


@pytest.mark.django_db
def test_clean_upload_passes(clamd, api_client, django_capture_on_commit_callbacks):
    files = [SimpleUploadedFile("a.zip", zip_bytes({"a.txt": b"salom"}))]
    task = post(api_client, "archive-extract", files, django_capture_on_commit_callbacks).data
    assert api_client.get(f"/api/v1/tasks/{task['id']}/").data["status"] == "done"
