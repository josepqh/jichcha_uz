"""Who is making the request: a registered user or an anonymous guest.

Guests get a random token in a signed, httpOnly cookie. Only its SHA-256 is stored,
so a database leak does not let anyone impersonate a guest.
"""

import hashlib
import secrets
from dataclasses import dataclass

from django.conf import settings
from django.http import HttpRequest, HttpResponse

from .models import LimitPolicy

_SALT = "uv-guest-v1"


def _hash(token: str) -> str:
    return hashlib.sha256(token.encode()).hexdigest()


@dataclass(frozen=True)
class Requester:
    user: object | None
    guest_key: str
    new_guest_token: str | None = None

    @property
    def is_registered(self) -> bool:
        return self.user is not None

    @property
    def role(self) -> str:
        return LimitPolicy.Role.REGISTERED if self.is_registered else LimitPolicy.Role.GUEST

    @property
    def subject(self) -> str:
        return f"u:{self.user.pk}" if self.user is not None else f"g:{self.guest_key}"

    def owner_filter(self) -> dict:
        if self.user is not None:
            return {"user": self.user}
        return {"user__isnull": True, "guest_key": self.guest_key}


def guest_key_from_cookie(request: HttpRequest) -> str:
    """Hash of this browser's guest token, or "" when there is no valid (signed) cookie."""
    token = request.get_signed_cookie(settings.GUEST_COOKIE_NAME, default=None, salt=_SALT)
    return _hash(token) if token else ""


def resolve_requester(request: HttpRequest, *, create_guest: bool = False) -> Requester:
    user = getattr(request, "user", None)
    if user is not None and user.is_authenticated:
        return Requester(user=user, guest_key="")
    token = request.get_signed_cookie(settings.GUEST_COOKIE_NAME, default=None, salt=_SALT)
    if token:
        return Requester(user=None, guest_key=_hash(token))
    if not create_guest:
        return Requester(user=None, guest_key="")
    token = secrets.token_urlsafe(32)
    return Requester(user=None, guest_key=_hash(token), new_guest_token=token)


def attach_guest_cookie(response: HttpResponse, requester: Requester) -> HttpResponse:
    if requester.new_guest_token:
        response.set_signed_cookie(
            settings.GUEST_COOKIE_NAME,
            requester.new_guest_token,
            salt=_SALT,
            max_age=settings.GUEST_COOKIE_MAX_AGE,
            httponly=True,
            secure=settings.GUEST_COOKIE_SECURE,
            samesite="Lax",
        )
    return response
