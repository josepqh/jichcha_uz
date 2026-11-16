"""Dashboard numbers (F-70), computed from tasks (kept TASK_HISTORY_DAYS = 30 days) and users."""

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import CharField, Count, Q
from django.db.models.functions import Cast, Coalesce, TruncDate
from django.utils import timezone

from apps.conversions.models import Task

FAILED = Task.Status.FAILED
# One "subject" per person: the account, else the guest browser / Telegram user.
SUBJECT = Coalesce(Cast("user_id", CharField()), "guest_key")


def dashboard(days: int) -> dict:
    since = timezone.now() - timedelta(days=days)
    tasks = Task.objects.filter(created_at__gte=since)

    per_day = (
        tasks.annotate(day=TruncDate("created_at"))
        .values("day")
        .annotate(tasks=Count("id"), failed=Count("id", filter=Q(status=FAILED)), active=Count(SUBJECT, distinct=True))
        .order_by("day")
    )
    top_tools = (
        tasks.values("tool")
        .annotate(count=Count("id"), failed=Count("id", filter=Q(status=FAILED)))
        .order_by("-count", "tool")[:10]
    )
    totals = tasks.aggregate(
        tasks=Count("id"),
        failed=Count("id", filter=Q(status=FAILED)),
        active=Count(SUBJECT, distinct=True),
        telegram_users=Count("guest_key", filter=Q(source=Task.Source.TELEGRAM), distinct=True),
        web_tasks=Count("id", filter=Q(source=Task.Source.WEB)),
        telegram_tasks=Count("id", filter=Q(source=Task.Source.TELEGRAM)),
    )
    users = get_user_model().objects
    # Every day of the period, including quiet ones, so the chart's time axis is even.
    found = {row["day"]: row for row in per_day}
    today = timezone.localdate()
    calendar = [today - timedelta(days=offset) for offset in range(days - 1, -1, -1)]
    return {
        "days": days,
        "per_day": [
            {"date": day.isoformat(), **{k: found.get(day, {}).get(k, 0) for k in ("tasks", "failed", "active")}}
            for day in calendar
        ],
        "top_tools": list(top_tools),
        "totals": {
            **totals,
            "error_rate": round(totals["failed"] / totals["tasks"], 4) if totals["tasks"] else 0.0,
            "registered_users": users.count(),
            "new_users": users.filter(date_joined__gte=since).count(),
        },
    }
