"""MAIL_BACKEND: short names and full paths both work, in settings and in the production gate."""

import pytest

from config.mail import is_smtp, resolve_backend
from tests.test_check_env import GOOD, check_env

SMTP = "django.core.mail.backends.smtp.EmailBackend"


@pytest.mark.parametrize(
    ("value", "expected"),
    [
        ("smtp", SMTP),
        (" SMTP ", SMTP),
        ("console", "django.core.mail.backends.console.EmailBackend"),
        (SMTP, SMTP),
        ("django.core.mail.backends.locmem.EmailBackend", "django.core.mail.backends.locmem.EmailBackend"),
    ],
)
def test_resolve_backend(value, expected):
    assert resolve_backend(value) == expected


def test_is_smtp():
    assert is_smtp("smtp") and is_smtp(SMTP)
    assert not is_smtp("console")


@pytest.mark.parametrize("backend", ["smtp", SMTP])
def test_gate_accepts_short_and_full_smtp(tmp_path, backend):
    errors, _ = check_env.check({**GOOD, "MAIL_BACKEND": backend}, tmp_path)
    assert not [e for e in errors if e.startswith("Email")]


@pytest.mark.parametrize("env", [{"MAIL_BACKEND": "console"}, {"SMTP_HOST": ""}])
def test_gate_rejects_console_or_missing_host(tmp_path, env):
    errors, _ = check_env.check({**GOOD, **env}, tmp_path)
    assert any(e.startswith("Email") for e in errors)
