"""MAIL_BACKEND accepts a short name ("smtp", "console") or a full Django backend path."""

ALIASES = {
    "smtp": "django.core.mail.backends.smtp.EmailBackend",
    "console": "django.core.mail.backends.console.EmailBackend",
}


def resolve_backend(value: str) -> str:
    value = value.strip()
    return ALIASES.get(value.lower(), value)


def is_smtp(value: str) -> bool:
    return resolve_backend(value) == ALIASES["smtp"]
