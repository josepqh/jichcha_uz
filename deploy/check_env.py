"""Check .env before a production start: python3 deploy/check_env.py [path/to/.env]

Errors (exit 1) are things that would make the site insecure or broken; warnings are things to
decide on. Standard library only, so it runs on a fresh server before anything is installed.
"""

import sys
from pathlib import Path

DEV_ONLY = (
    "THROTTLE_AUTH",
    "THROTTLE_TASK_CREATE",
    "THROTTLE_TASK_CREATE_IP",
    "THROTTLE_ANON",
    "THROTTLE_ANON_IP",
    "THROTTLE_FEEDBACK",
)


def read_env(path: Path) -> dict[str, str]:
    values = {}
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if line and not line.startswith("#") and "=" in line:
            key, value = line.split("=", 1)
            values[key.strip()] = value.strip()
    return values


def check(env: dict[str, str], root: Path) -> tuple[list[str], list[str]]:
    errors: list[str] = []
    warnings: list[str] = []
    get = env.get

    domain = get("DOMAIN", "")
    if not domain or "example" in domain or domain.startswith(("localhost", "127.")):
        errors.append("DOMAIN: set the real domain (e.g. universe.uz).")
    if (
        len(get("DJANGO_SECRET_KEY", "")) < 50
        or "change" in get("DJANGO_SECRET_KEY", "").lower()
    ):
        errors.append(
            "DJANGO_SECRET_KEY: at least 50 random characters "
            "(python3 -c 'import secrets; print(secrets.token_urlsafe(64))')."
        )
    if len(get("POSTGRES_PASSWORD", "")) < 16:
        errors.append("POSTGRES_PASSWORD: at least 16 random characters.")
    if get("DJANGO_DEBUG", "").lower() in ("1", "true", "yes"):
        errors.append("DJANGO_DEBUG must be off in production.")
    for key in ("GUEST_COOKIE_SECURE", "AUTH_COOKIE_SECURE", "SECURE_SSL_REDIRECT"):
        if get(key, "").lower() in ("0", "false", "no"):
            errors.append(
                f"{key}=false: remove it; production must use secure cookies and HTTPS."
            )
    relaxed = [k for k in DEV_ONLY if k in env]
    if relaxed:
        errors.append(
            f"Development throttle overrides present ({', '.join(relaxed)}): remove them to use the safe defaults."
        )
    if get("PUBLIC_ORIGIN", "").startswith("http://"):
        warnings.append(
            "PUBLIC_ORIGIN is http://; compose.prod.yaml sets https://DOMAIN, but fix .env too."
        )

    if get("MAIL_BACKEND", "console") == "console" or not get("SMTP_HOST"):
        errors.append(
            "Email: set MAIL_BACKEND=smtp and SMTP_HOST/SMTP_USER/SMTP_PASSWORD, or password reset mails go nowhere."
        )
    for key in ("VITE_LEGAL_NAME", "VITE_CONTACT_EMAIL"):
        if not get(key):
            errors.append(f"{key}: required on the privacy policy and terms pages.")

    if get("TELEGRAM_BOT_TOKEN"):
        if len(get("BOT_API_SECRET", "")) < 32:
            errors.append(
                "BOT_API_SECRET: at least 32 random characters when the bot is on."
            )
        if len(get("TELEGRAM_WEBHOOK_SECRET", "")) < 16:
            errors.append(
                "TELEGRAM_WEBHOOK_SECRET: at least 16 random characters (webhook mode)."
            )
    else:
        warnings.append("TELEGRAM_BOT_TOKEN empty: the bot stays off.")
    if not get("ALERT_TELEGRAM_CHAT_ID"):
        warnings.append(
            "ALERT_TELEGRAM_CHAT_ID empty: server alerts only go to the monitor's log."
        )
    if bool(get("TURNSTILE_SECRET_KEY")) != bool(get("VITE_TURNSTILE_SITE_KEY")):
        errors.append(
            "Turnstile: set both TURNSTILE_SECRET_KEY and VITE_TURNSTILE_SITE_KEY, or neither."
        )
    if get("STAFF_REQUIRE_2FA", "").lower() in ("0", "false", "no"):
        errors.append("STAFF_REQUIRE_2FA=false: remove it; staff must use two-step sign-in in production.")
    admin_url = get("DJANGO_ADMIN_URL", "")
    if admin_url and (not admin_url.startswith("admin/") or admin_url.strip("/") == "admin"):
        errors.append(
            "DJANGO_ADMIN_URL: leave empty (off), or use admin/<something hard to guess>/ (nginx routes admin/)."
        )
    if not get("SENTRY_DSN"):
        warnings.append("SENTRY_DSN empty: errors are not collected anywhere but logs.")
    if not (root / "backup.env").is_file():
        warnings.append("backup.env missing: database dumps stay on this server only.")
    return errors, warnings


def main() -> int:
    path = (
        Path(sys.argv[1])
        if len(sys.argv) > 1
        else Path(__file__).resolve().parents[1] / ".env"
    )
    if not path.is_file():
        print(f"No {path}. Copy .env.example to .env first.")
        return 1
    errors, warnings = check(read_env(path), path.parent)
    for line in errors:
        print(f"ERROR   {line}")
    for line in warnings:
        print(f"warning {line}")
    print(
        "OK: ready for production."
        if not errors
        else f"{len(errors)} problem(s) to fix before going live."
    )
    return 1 if errors else 0


if __name__ == "__main__":
    sys.exit(main())
