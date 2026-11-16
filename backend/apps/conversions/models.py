import uuid
from pathlib import PurePath

from django.conf import settings
from django.db import models
from django.db.models import Q


class LimitPolicy(models.Model):
    """Anti-abuse limits per role. The platform is free; these only protect the servers."""

    class Role(models.TextChoices):
        GUEST = "guest", "Guest"
        REGISTERED = "registered", "Registered"

    role = models.CharField(max_length=20, choices=Role.choices, unique=True)
    max_file_mb = models.PositiveIntegerField()
    max_total_mb = models.PositiveIntegerField(help_text="Upper bound for one request (all files).")
    daily_tasks = models.PositiveIntegerField()
    max_batch = models.PositiveIntegerField()
    retention_hours = models.PositiveIntegerField()
    daily_ocr_pages = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "limit_policies"
        constraints = [
            models.CheckConstraint(
                condition=Q(max_file_mb__gt=0)
                & Q(max_total_mb__gte=models.F("max_file_mb"))
                & Q(daily_tasks__gt=0)
                & Q(max_batch__gt=0)
                & Q(retention_hours__gt=0),
                name="limit_policies_positive",
            ),
        ]

    def __str__(self) -> str:
        return self.role


class TaskQuerySet(models.QuerySet["Task"]):
    def owned_by(self, *, user=None, guest_key: str | None = None) -> TaskQuerySet:
        if user is not None and user.is_authenticated:
            return self.filter(user=user)
        if guest_key:
            return self.filter(user__isnull=True, guest_key=guest_key)
        return self.none()


class Task(models.Model):
    class Status(models.TextChoices):
        QUEUED = "queued", "Queued"
        PROCESSING = "processing", "Processing"
        DONE = "done", "Done"
        FAILED = "failed", "Failed"

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, null=True, blank=True, on_delete=models.CASCADE, related_name="tasks"
    )
    # SHA-256 of the guest cookie token; empty for registered users.
    guest_key = models.CharField(max_length=64, blank=True, default="")
    tool = models.CharField(max_length=64)
    options = models.JSONField(default=dict, blank=True)
    status = models.CharField(max_length=20, choices=Status.choices, default=Status.QUEUED)
    error_code = models.CharField(max_length=64, blank=True, default="")
    duration_ms = models.PositiveIntegerField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)
    expires_at = models.DateTimeField()
    files_purged_at = models.DateTimeField(null=True, blank=True)

    objects = TaskQuerySet.as_manager()

    class Meta:
        db_table = "tasks"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["user", "-created_at"], name="tasks_user_created_idx"),
            models.Index(
                fields=["guest_key", "-created_at"],
                name="tasks_guest_created_idx",
                condition=Q(user__isnull=True),
            ),
            models.Index(fields=["expires_at"], name="tasks_expiring_idx", condition=Q(files_purged_at__isnull=True)),
            models.Index(fields=["created_at"], name="tasks_failed_idx", condition=Q(status="failed")),
        ]
        constraints = [
            models.CheckConstraint(condition=Q(user__isnull=False) | ~Q(guest_key=""), name="tasks_has_owner"),
            models.CheckConstraint(
                condition=Q(status__in=["queued", "processing", "done", "failed"]), name="tasks_status_valid"
            ),
        ]

    def __str__(self) -> str:
        return f"{self.tool} {self.id} ({self.status})"


def task_file_path(instance: TaskFile, filename: str) -> str:
    # Stored names never contain user input: only ids and a whitelisted extension.
    ext = PurePath(filename).suffix.lower()[:10]
    return f"tasks/{instance.task_id}/{instance.role}/{instance.id}{ext}"


class TaskFile(models.Model):
    class Role(models.TextChoices):
        INPUT = "input", "Input"
        OUTPUT = "output", "Output"
        BUNDLE = "bundle", "Bundle (zip of outputs)"

    id = models.UUIDField(primary_key=True, default=uuid.uuid7, editable=False)
    task = models.ForeignKey(Task, on_delete=models.CASCADE, related_name="files")
    role = models.CharField(max_length=10, choices=Role.choices)
    file = models.FileField(upload_to=task_file_path, max_length=255)
    original_name = models.CharField(max_length=255)
    mime_type = models.CharField(max_length=100)
    size_bytes = models.BigIntegerField()
    position = models.PositiveIntegerField(default=0)

    class Meta:
        db_table = "task_files"
        ordering = ["position"]
        constraints = [
            models.CheckConstraint(condition=Q(size_bytes__gte=0), name="task_files_size_non_negative"),
        ]

    def __str__(self) -> str:
        return f"{self.role}: {self.original_name}"


class UsageCounter(models.Model):
    """Per-subject daily counter. subject is 'u:<user id>' or 'g:<guest key>'."""

    subject = models.CharField(max_length=80)
    day = models.DateField()
    tasks_count = models.PositiveIntegerField(default=0)
    bytes_processed = models.BigIntegerField(default=0)

    class Meta:
        db_table = "usage_counters"
        constraints = [
            models.UniqueConstraint(fields=["subject", "day"], name="usage_counters_subject_day_uniq"),
        ]

    def __str__(self) -> str:
        return f"{self.subject} {self.day}: {self.tasks_count}"
