"""Run the bot: `python -m universe_bot`. Polling unless TELEGRAM_WEBHOOK_URL is set."""

import asyncio
import logging

from .app import run_polling, run_webhook
from .config import Settings


def main() -> None:
    logging.basicConfig(level=logging.INFO, format="%(asctime)s %(levelname)s %(name)s %(message)s")
    settings = Settings.from_env()
    if settings.webhook_url:
        run_webhook(settings)
    else:
        asyncio.run(run_polling(settings))


if __name__ == "__main__":
    main()
