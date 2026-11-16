"""Sentry event scrubbing. The privacy policy promises error reports carry no personal data."""


def scrub_event(event: dict, _hint: object) -> dict:
    """Drop cookies, headers, bodies, query strings (download links carry a signed token) and the user."""
    request = event.get("request") or {}
    for key in ("cookies", "headers", "data", "query_string", "env"):
        request.pop(key, None)
    event.pop("user", None)
    # The Celery integration attaches task args/kwargs here; a kwarg can be a file password.
    event.pop("extra", None)
    (event.get("contexts") or {}).pop("celery-job", None)
    return event
