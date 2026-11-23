"""Settings from the environment (the project's .env in development, compose in Docker)."""

import os
from dataclasses import dataclass
from pathlib import Path


def _load_dotenv(path: Path) -> None:
    """Minimal .env reader for local runs; real environment variables always win."""
    if not path.is_file():
        return
    for line in path.read_text(encoding="utf-8").splitlines():
        line = line.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        os.environ.setdefault(key.strip(), value.strip())


@dataclass(frozen=True)
class Settings:
    bot_token: str
    backend_url: str  # how the bot reaches the API (inside Docker: http://backend:8000)
    public_origin: str  # links shown to users (the website)
    bot_api_secret: str
    redis_url: str
    webhook_url: str  # empty = long polling
    webhook_secret: str
    webhook_host: str
    webhook_port: int
    # Telegram limits: bots download files up to 20 MB and upload up to 50 MB.
    max_download_mb: int = 20
    max_upload_mb: int = 50
    task_timeout_s: int = 330  # longest tool time limit (300 s) plus queueing

    @classmethod
    def from_env(cls) -> Settings:
        _load_dotenv(Path(__file__).resolve().parents[2] / ".env")
        env = os.environ
        token = env.get("TELEGRAM_BOT_TOKEN", "")
        secret = env.get("BOT_API_SECRET", "")
        if not token or not secret:
            raise SystemExit("Set TELEGRAM_BOT_TOKEN and BOT_API_SECRET (see .env.example).")
        return cls(
            bot_token=token,
            backend_url=env.get("BOT_BACKEND_URL", "http://localhost:8000").rstrip("/"),
            public_origin=env.get("PUBLIC_ORIGIN", "http://localhost:5173").rstrip("/"),
            bot_api_secret=secret,
            redis_url=env.get("BOT_REDIS_URL") or env.get("REDIS_URL", "redis://localhost:6379/0"),
            webhook_url=env.get("TELEGRAM_WEBHOOK_URL", ""),
            webhook_secret=env.get("TELEGRAM_WEBHOOK_SECRET", ""),
            webhook_host=env.get("BOT_WEBHOOK_HOST", "0.0.0.0"),  # noqa: S104 - inside the container
            webhook_port=int(env.get("BOT_WEBHOOK_PORT", "8081")),
        )
