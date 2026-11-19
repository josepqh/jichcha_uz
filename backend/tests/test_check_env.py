"""deploy/check_env.py: the production .env gate."""

import importlib.util
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
spec = importlib.util.spec_from_file_location("check_env", ROOT / "deploy" / "check_env.py")
check_env = importlib.util.module_from_spec(spec)
spec.loader.exec_module(check_env)

GOOD = {
    "DOMAIN": "universe.uz",
    "DJANGO_SECRET_KEY": "x" * 64,
    "POSTGRES_PASSWORD": "p" * 24,
    "MAIL_BACKEND": "smtp",
    "SMTP_HOST": "smtp.universe.uz",
    "VITE_LEGAL_NAME": "jichcha MChJ",
    "VITE_CONTACT_EMAIL": "support@universe.uz",
}


def test_good_config_passes(tmp_path):
    errors, _ = check_env.check(GOOD, tmp_path)
    assert errors == []


def test_catches_dev_leftovers_and_weak_secrets(tmp_path):
    env = {**GOOD, "THROTTLE_AUTH": "500/15m", "GUEST_COOKIE_SECURE": "false", "DJANGO_SECRET_KEY": "short"}
    errors, _ = check_env.check(env, tmp_path)
    text = " ".join(errors)
    assert "THROTTLE_AUTH" in text and "GUEST_COOKIE_SECURE" in text and "DJANGO_SECRET_KEY" in text


def test_bot_and_turnstile_pairs(tmp_path):
    errors, _ = check_env.check({**GOOD, "TELEGRAM_BOT_TOKEN": "1:x", "TURNSTILE_SECRET_KEY": "s"}, tmp_path)
    text = " ".join(errors)
    assert "BOT_API_SECRET" in text and "TELEGRAM_WEBHOOK_SECRET" in text and "Turnstile" in text


def test_admin_security_overrides(tmp_path):
    errors, _ = check_env.check({**GOOD, "STAFF_REQUIRE_2FA": "false", "DJANGO_ADMIN_URL": "admin/"}, tmp_path)
    assert any("STAFF_REQUIRE_2FA" in e for e in errors)
    assert any("DJANGO_ADMIN_URL" in e for e in errors)
    errors, _ = check_env.check({**GOOD, "DJANGO_ADMIN_URL": "admin/k3x9-console/"}, tmp_path)
    assert not any("DJANGO_ADMIN_URL" in e for e in errors)
