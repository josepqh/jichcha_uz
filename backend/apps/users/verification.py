"""Signed, expiring email-confirmation tokens. No table: the signature and the address hash are the proof."""

import hashlib

from django.core import signing

from .models import User

SALT = "users.email-verify"
MAX_AGE = 3 * 24 * 3600


def _email_hash(email: str) -> str:
    # The link names the address only by hash, so it doesn't leak into logs; changing the
    # address would also make old links useless.
    return hashlib.sha256(email.lower().encode()).hexdigest()[:24]


def make_token(user: User) -> str:
    return signing.dumps({"u": str(user.pk), "h": _email_hash(user.email)}, salt=SALT, compress=True)


def user_for_token(token: str) -> User | None:
    try:
        data = signing.loads(token, salt=SALT, max_age=MAX_AGE)
    except signing.BadSignature:  # also covers SignatureExpired
        return None
    user = User.objects.filter(pk=data.get("u"), is_active=True).first()
    if user is None or data.get("h") != _email_hash(user.email):
        return None
    return user
