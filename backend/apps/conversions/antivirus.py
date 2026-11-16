"""Malware scanning through ClamAV's daemon (clamd), INSTREAM over TCP.

Uploads are scanned on the worker before any converter opens them. When scanning is enabled and
clamd cannot answer, the task fails ("scan_unavailable"): unscanned files are never processed.
clamd unpacks archives and office files itself, so a scan of the upload covers what is inside.
"""

import logging
import socket
import struct
from pathlib import Path

from django.conf import settings

logger = logging.getLogger(__name__)

CHUNK = 64 * 1024


class ScanUnavailableError(Exception):
    """clamd is down, timed out, or answered something we do not understand."""


def enabled() -> bool:
    return bool(settings.CLAMAV_HOST)


def scan_file(path: Path) -> str | None:
    """Return the signature name if the file is infected, None if it is clean."""
    try:
        with socket.create_connection((settings.CLAMAV_HOST, settings.CLAMAV_PORT), settings.CLAMAV_TIMEOUT) as sock:
            sock.sendall(b"zINSTREAM\0")
            with path.open("rb") as fh:
                while chunk := fh.read(CHUNK):
                    sock.sendall(struct.pack("!I", len(chunk)) + chunk)
            sock.sendall(struct.pack("!I", 0))
            reply = b""
            while not reply.endswith(b"\0"):
                data = sock.recv(4096)
                if not data:
                    break
                reply += data
    except OSError as exc:
        raise ScanUnavailableError(str(exc)) from exc

    text = reply.rstrip(b"\0").decode("utf-8", "replace").strip()
    if text.endswith(" OK"):
        return None
    if text.endswith(" FOUND"):
        return text.removeprefix("stream:").removesuffix("FOUND").strip()
    # e.g. "INSTREAM size limit exceeded. ERROR": clamd's StreamMaxLength is below our upload limit.
    raise ScanUnavailableError(text or "empty reply")
