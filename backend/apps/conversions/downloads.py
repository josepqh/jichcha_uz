"""Signed download links.

A plain <a download> link cannot carry the user's Authorization header, so each output gets a
capability URL: the signature binds the file id to the task's expiry time and dies with the file.
"""

from datetime import datetime

from django.core import signing
from django.urls import reverse
from django.utils import timezone

_SALT = "jichcha-download-v1"


def signed_download_url(file_id, expires_at: datetime) -> str:
    token = signing.dumps({"f": str(file_id), "e": int(expires_at.timestamp())}, salt=_SALT)
    return f"{reverse('file-download', kwargs={'file_id': file_id})}?t={token}"


def verify_download_token(token: str, file_id) -> bool:
    try:
        payload = signing.loads(token, salt=_SALT)
    except signing.BadSignature:
        return False
    if not isinstance(payload, dict) or payload.get("f") != str(file_id):
        return False
    expires = payload.get("e")
    return isinstance(expires, int) and expires > timezone.now().timestamp()
