"""Alerting loop: run the checks every few minutes and tell the team on Telegram.

Runs in its own container on the default network (the workers have no internet on purpose).
An alert is sent when a check starts failing and once more when it recovers; nothing repeats
while the state stays the same, so a long outage is one message, not a flood.
"""

import logging
import time

import requests
from django.conf import settings
from django.core.management.base import BaseCommand

from apps.staff.monitoring import CHECKS

logger = logging.getLogger(__name__)


def send(text: str) -> bool:
    token, chat = settings.ALERT_TELEGRAM_TOKEN, settings.ALERT_TELEGRAM_CHAT_ID
    if not token or not chat:
        logger.warning("ALERT (Telegram not configured): %s", text)
        return False
    try:
        resp = requests.post(
            f"https://api.telegram.org/bot{token}/sendMessage",
            json={"chat_id": chat, "text": text, "disable_web_page_preview": True},
            timeout=10,
        )
        return resp.ok
    except requests.RequestException:
        logger.exception("Could not deliver an alert")
        return False


def run_checks(state: dict[str, str | None], site: str) -> list[str]:
    """One round. `state` maps check -> current problem; returns the messages it sent."""
    sent = []
    for name, check in CHECKS.items():
        try:
            problem = check()
        except Exception as exc:  # noqa: BLE001 - a broken check is itself a problem
            problem = f"Check crashed: {exc.__class__.__name__}"
        before = state.get(name)
        if problem and problem != before:
            message = f"🔴 Universe ({site}) — {name}: {problem}"
        elif before and not problem:
            message = f"✅ Universe ({site}) — {name} is OK again."
        else:
            continue
        state[name] = problem
        send(message)
        sent.append(message)
    return sent


class Command(BaseCommand):
    help = "Watch health, queues, workers, antivirus and error rate; alert on Telegram."

    def add_arguments(self, parser):
        parser.add_argument("--interval", type=int, default=300, help="Seconds between rounds.")
        parser.add_argument("--once", action="store_true", help="Run one round and exit.")

    def handle(self, *args, interval: int, once: bool, **options):
        state: dict[str, str | None] = {}
        site = settings.PUBLIC_ORIGIN
        while True:
            for message in run_checks(state, site):
                self.stdout.write(message)
            if once:
                return
            time.sleep(interval)
