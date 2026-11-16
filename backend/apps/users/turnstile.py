"""Cloudflare Turnstile check for sign-up and password-reset forms (anti-bot, optional).

Off unless TURNSTILE_SECRET_KEY is set. When on, a form without a valid token is refused.
If Cloudflare can't be reached the check fails closed: refusing a sign-up for a minute is
better than letting a script create thousands of accounts.
"""

import logging

import requests
from django.conf import settings
from rest_framework import status

from apps.core.exceptions import AppError

logger = logging.getLogger(__name__)
VERIFY_URL = "https://challenges.cloudflare.com/turnstile/v0/siteverify"


def enabled() -> bool:
    return bool(settings.TURNSTILE_SECRET_KEY)


def require(token: str | None, remote_ip: str | None) -> None:
    if not enabled():
        return
    if not token or len(token) > 2048:
        raise AppError("captcha_required", "Please confirm you are not a robot.", status.HTTP_400_BAD_REQUEST)
    try:
        resp = requests.post(
            VERIFY_URL,
            data={"secret": settings.TURNSTILE_SECRET_KEY, "response": token, "remoteip": remote_ip or ""},
            timeout=10,
        )
        ok = resp.ok and resp.json().get("success") is True
    except requests.RequestException, ValueError:
        logger.warning("Turnstile unreachable")
        ok = False
    if not ok:
        raise AppError("captcha_failed", "The robot check failed. Try again.", status.HTTP_400_BAD_REQUEST)
