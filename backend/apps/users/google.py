"""Verify a Google Identity Services ID token (the `credential` from the GIS button)."""

from dataclasses import dataclass

from django.conf import settings
from google.auth.exceptions import GoogleAuthError
from google.auth.transport import requests as google_requests
from google.oauth2 import id_token

_ISSUERS = {"accounts.google.com", "https://accounts.google.com"}


class GoogleTokenError(Exception):
    pass


@dataclass(frozen=True)
class GoogleIdentity:
    email: str
    subject: str
    issued_at: int = 0  # "iat" claim, seconds since the epoch


def verify_credential(credential: str) -> GoogleIdentity:
    try:
        info = id_token.verify_oauth2_token(credential, google_requests.Request(), settings.GOOGLE_CLIENT_ID)
    except (ValueError, GoogleAuthError) as exc:
        raise GoogleTokenError("invalid token") from exc
    if info.get("iss") not in _ISSUERS:
        raise GoogleTokenError("wrong issuer")
    if not info.get("email") or not info.get("email_verified"):
        raise GoogleTokenError("email not verified")
    return GoogleIdentity(email=info["email"].lower(), subject=info["sub"], issued_at=int(info.get("iat", 0)))
