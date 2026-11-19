"""Time-based one-time codes (RFC 6238: SHA-1, 6 digits, 30 s) for two-step sign-in."""

import base64
import hashlib
import hmac
import secrets
import struct
import time
from urllib.parse import quote, urlencode

import segno
from django.core.cache import cache
from rest_framework import status

from apps.core.exceptions import AppError

from .models import User

STEP = 30
DIGITS = 6
ISSUER = "jichcha"
# Wrong codes allowed per account before a pause, and the pause length (seconds).
MAX_FAILURES = 5
LOCK_SECONDS = 15 * 60


def new_secret() -> str:
    return base64.b32encode(secrets.token_bytes(20)).decode()


def code_at(secret: str, counter: int) -> str:
    digest = hmac.new(base64.b32decode(secret), struct.pack(">Q", counter), hashlib.sha1).digest()
    offset = digest[-1] & 0x0F
    number = struct.unpack(">I", digest[offset : offset + 4])[0] & 0x7FFFFFFF
    return f"{number % 10**DIGITS:0{DIGITS}d}"


def matching_step(secret: str, code: str, now: float | None = None) -> int | None:
    """The time step the code belongs to, allowing one step of clock drift either way."""
    code = "".join(ch for ch in code if not ch.isspace())
    if not secret or len(code) != DIGITS or not code.isdigit():
        return None
    current = int((time.time() if now is None else now) // STEP)
    for counter in (current - 1, current, current + 1):
        if hmac.compare_digest(code_at(secret, counter), code):
            return counter
    return None


def provisioning_uri(secret: str, email: str) -> str:
    label = quote(f"{ISSUER}:{email}")
    query = urlencode({"secret": secret, "issuer": ISSUER, "digits": DIGITS, "period": STEP})
    return f"otpauth://totp/{label}?{query}"


def qr_data_uri(uri: str) -> str:
    return segno.make(uri, error="m").svg_data_uri(scale=5, border=2)


def _failures_key(user: User) -> str:
    return f"auth:otp-fail:{user.pk}"


def check_code(user: User, code: str | None) -> None:
    """Accept a fresh code for the user's confirmed or pending secret, or raise AppError.

    Each code works once: the step is stored with a conditional update, so two requests racing
    with the same code cannot both pass.
    """
    if not code:
        raise AppError("otp_required", "Enter the code from your authenticator app.", status.HTTP_401_UNAUTHORIZED)
    key = _failures_key(user)
    if cache.get(key, 0) >= MAX_FAILURES:
        raise AppError("otp_locked", "Too many wrong codes. Try again later.", status.HTTP_429_TOO_MANY_REQUESTS)
    step = matching_step(user.totp_secret, code)
    if step is not None and User.objects.filter(pk=user.pk, totp_last_step__lt=step).update(totp_last_step=step):
        user.totp_last_step = step
        cache.delete(key)
        return
    if cache.add(key, 1, LOCK_SECONDS) is False:
        try:
            cache.incr(key)
        except ValueError:
            cache.set(key, 1, LOCK_SECONDS)
    raise AppError("otp_invalid", "That code is not right.", status.HTTP_401_UNAUTHORIZED)


def require_for(user: User, code: str | None) -> None:
    """Second step of any sign-in that would hand out a session."""
    if user.totp_enabled:
        check_code(user, code)
