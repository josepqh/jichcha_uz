"""Every task must land on a queue some worker reads (compose.yaml: light, maintenance, office, mail).

A task without a route goes to Celery's default "celery" queue, which no worker consumes, so it
is accepted and then silently never runs.
"""

import re
from pathlib import Path

from config.celery import app

COMPOSE = Path(__file__).resolve().parents[2] / "compose.yaml"


def consumed_queues() -> set[str]:
    queues: set[str] = set()
    for match in re.finditer(r'"-Q", "([^"]+)"', COMPOSE.read_text()):
        queues.update(match.group(1).split(","))
    return queues


def test_compose_workers_read_the_known_queues():
    assert consumed_queues() == {"light", "maintenance", "office", "mail"}


def test_email_tasks_go_to_the_mail_queue():
    # Only the mailer can reach SMTP; the file workers are on a network with no internet.
    app.loader.import_default_modules()
    for name in ("apps.core.feedback.send_feedback", "apps.users.tasks.send_password_reset"):
        assert app.amqp.router.route({}, name, args=(), kwargs={})["queue"].name == "mail"


def test_every_task_is_routed_to_a_consumed_queue():
    app.loader.import_default_modules()  # runs autodiscovery, as a worker does on start
    names = sorted(n for n in app.tasks if n.startswith("apps."))
    assert "apps.core.feedback.send_feedback" in names
    queues = consumed_queues()
    unrouted = {
        name: queue
        for name in names
        if (queue := app.amqp.router.route({}, name, args=(), kwargs={})["queue"].name) not in queues
    }
    assert unrouted == {}
