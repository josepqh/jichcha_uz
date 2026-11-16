"""Business logic for creating, processing and purging conversion tasks."""

import logging
import shutil
import time
import zipfile
from dataclasses import dataclass
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.files import File
from django.core.files.uploadedfile import UploadedFile
from django.db import transaction
from django.db.models import F
from django.utils import timezone
from rest_framework import status

from apps.core.exceptions import AppError

from . import antivirus
from .formats import ZIP_MIME, DetectedFile, ImageTooLargeError, detect_file
from .identity import Requester
from .models import LimitPolicy, Task, TaskFile, ToolSetting, UsageCounter
from .processors.base import InputFile, OutputFile, ProcessingError, safe_name, safe_relpath
from .tools import Tool, get_tool

logger = logging.getLogger(__name__)

MB = 1024 * 1024


def disabled_tools() -> set[str]:
    """Tools an admin switched off (F-75). One small query; the table has a row per changed tool."""
    return set(ToolSetting.objects.filter(enabled=False).values_list("slug", flat=True))


def get_policy(role: str) -> LimitPolicy:
    return LimitPolicy.objects.get(role=role)


def max_files_for(tool: Tool, policy: LimitPolicy) -> int:
    return min(policy.max_batch, tool.max_files or policy.max_batch)


def usage_today(requester: Requester) -> int:
    row = UsageCounter.objects.filter(subject=requester.subject, day=timezone.localdate()).first()
    return row.tasks_count if row else 0


def check_request_size(content_length: str | None, policy: LimitPolicy) -> None:
    """Reject oversized bodies from the header, before Django spools the upload to disk."""
    try:
        length = int(content_length or 0)
    except ValueError:
        length = 0
    if length > policy.max_total_mb * MB:
        raise AppError(
            "request_too_large",
            "Request is too large.",
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            {"max_total_mb": policy.max_total_mb},
        )


@dataclass(frozen=True)
class ValidatedUpload:
    upload: UploadedFile
    detected: DetectedFile


def validate_uploads(tool: Tool, uploads: list[UploadedFile], policy: LimitPolicy) -> list[ValidatedUpload]:
    if not uploads:
        raise AppError("no_files", "Select at least one file.")
    if len(uploads) < tool.min_files:
        raise AppError("too_few_files", "Select more files.", details={"min_files": tool.min_files})
    limit = max_files_for(tool, policy)
    if len(uploads) > limit:
        raise AppError("too_many_files", "Too many files.", details={"max_files": limit})
    total = sum(u.size for u in uploads)
    if total > policy.max_total_mb * MB:
        raise AppError(
            "request_too_large",
            "Request is too large.",
            status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
            {"max_total_mb": policy.max_total_mb},
        )

    validated = []
    for upload in uploads:
        name = safe_name(upload.name or "file")
        if upload.size > policy.max_file_mb * MB:
            raise AppError(
                "file_too_large",
                "File is too large.",
                status.HTTP_413_REQUEST_ENTITY_TOO_LARGE,
                {"name": name, "max_file_mb": policy.max_file_mb},
            )
        if tool.accepts_any:
            # Packed as-is and never decoded, so the format does not matter.
            validated.append(ValidatedUpload(upload=upload, detected=DetectedFile(fmt="bin")))
            continue
        try:
            detected = detect_file(upload, name)
        except ImageTooLargeError:
            raise AppError(
                "image_too_large",
                "Image dimensions are too large.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {"name": name},
            ) from None
        if detected is None or detected.fmt not in tool.accepts:
            raise AppError(
                "unsupported_format",
                "This file type is not supported by the tool.",
                status.HTTP_415_UNSUPPORTED_MEDIA_TYPE,
                {"name": name},
            )
        if detected.pixels > settings.IMAGE_MAX_PIXELS:
            raise AppError(
                "image_too_large",
                "Image dimensions are too large.",
                status.HTTP_422_UNPROCESSABLE_ENTITY,
                {"name": name},
            )
        validated.append(ValidatedUpload(upload=upload, detected=detected))
    return validated


def _consume_daily_quota(requester: Requester, policy: LimitPolicy, nbytes: int) -> None:
    counter, _ = UsageCounter.objects.get_or_create(subject=requester.subject, day=timezone.localdate())
    updated = UsageCounter.objects.filter(pk=counter.pk, tasks_count__lt=policy.daily_tasks).update(
        tasks_count=F("tasks_count") + 1, bytes_processed=F("bytes_processed") + nbytes
    )
    if not updated:
        raise AppError(
            "daily_limit_reached",
            "Daily limit reached.",
            status.HTTP_429_TOO_MANY_REQUESTS,
            {"daily_tasks": policy.daily_tasks},
        )


def _server_options(policy: LimitPolicy) -> dict:
    """Limits the processor needs that depend on the caller's role. Clients cannot set these:
    option serializers drop unknown keys, and these are added after validation."""
    return {"_max_unpacked_mb": min(settings.ARCHIVE_MAX_UNPACKED_MB, policy.max_total_mb * 5)}


def create_task(
    requester: Requester, tool: Tool, options: dict, uploads: list[ValidatedUpload], policy: LimitPolicy
) -> Task:
    from .tasks import run_conversion  # avoid import cycle at module load

    with transaction.atomic():
        _consume_daily_quota(requester, policy, sum(v.upload.size for v in uploads))
        task = Task.objects.create(
            user=requester.user,
            guest_key=requester.guest_key,
            tool=tool.slug,
            options={**options, **_server_options(policy)},
            source=requester.source,
            input_meta=[{"format": item.detected.fmt, "size": item.upload.size} for item in uploads],
            expires_at=timezone.now() + timedelta(hours=policy.retention_hours),
        )
        for position, item in enumerate(uploads):
            ext = item.detected.ext
            tf = TaskFile(
                task=task,
                role=TaskFile.Role.INPUT,
                original_name=safe_name(item.upload.name or f"file.{ext}"),
                mime_type=item.detected.mime,
                size_bytes=item.upload.size,
                position=position,
            )
            tf.file.save(f"input.{ext}", item.upload, save=False)
            tf.save()
        transaction.on_commit(
            lambda: run_conversion.apply_async(
                args=[str(task.pk)],
                queue=tool.queue,
                soft_time_limit=tool.time_limit,
                time_limit=tool.time_limit + 30,
            )
        )
    return task


# --- Worker side ------------------------------------------------------------


def _unique_names(outputs: list[OutputFile]) -> list[str]:
    seen: dict[str, int] = {}
    names = []
    for out in outputs:
        name = safe_relpath(out.name)  # archive tools keep folders: "photos/img.jpg"
        count = seen.get(name.lower(), 0)
        seen[name.lower()] = count + 1
        if count:
            stem, dot, ext = name.rpartition(".")
            name = f"{stem} ({count + 1}).{ext}" if dot and "/" not in ext else f"{name} ({count + 1})"
        names.append(name)
    return names


def _materialize_inputs(task: Task, tool: Tool, workdir: Path) -> list[InputFile]:
    inputs = []
    for i, tf in enumerate(task.files.filter(role=TaskFile.Role.INPUT).order_by("position")):
        local = workdir / f"in-{i}"
        try:
            with tf.file.open("rb") as src, local.open("wb") as dst:
                shutil.copyfileobj(src, dst, length=MB)
        except FileNotFoundError as exc:
            raise ProcessingError("files_deleted") from exc
        if tool.accepts_any:
            inputs.append(InputFile(path=local, name=tf.original_name, fmt="bin"))
            continue
        with local.open("rb") as fh:
            try:
                detected = detect_file(fh, tf.original_name)
            except ImageTooLargeError as exc:
                raise ProcessingError("image_too_large") from exc
        if detected is None or detected.fmt not in tool.accepts:
            raise ProcessingError("unsupported_format")
        inputs.append(InputFile(path=local, name=tf.original_name, fmt=detected.fmt))
    if not inputs:
        raise ProcessingError("files_deleted")
    return inputs


def _scan_inputs(task: Task, inputs: list[InputFile]) -> None:
    if not antivirus.enabled():
        return
    for item in inputs:
        try:
            signature = antivirus.scan_file(item.path)
        except antivirus.ScanUnavailableError as exc:
            logger.error("Antivirus unavailable task=%s: %s", task.pk, exc)
            raise ProcessingError("scan_unavailable") from exc
        if signature:
            logger.warning("Malware rejected task=%s signature=%s", task.pk, signature)
            raise ProcessingError("malware_detected")


def _store_outputs(task: Task, outputs: list[OutputFile], workdir: Path) -> None:
    names = _unique_names(outputs)
    for position, (out, name) in enumerate(zip(outputs, names, strict=True)):
        tf = TaskFile(
            task=task,
            role=TaskFile.Role.OUTPUT,
            original_name=name,
            mime_type=out.mime,
            size_bytes=out.path.stat().st_size,
            position=position,
        )
        with out.path.open("rb") as fh:
            tf.file.save(name, File(fh), save=False)
        tf.save()
    tool = get_tool(task.tool)
    if len(outputs) > 1 and tool is not None and tool.bundle:
        bundle = workdir / "bundle.zip"
        # Images and PDFs are already compressed; storing is faster and barely larger.
        with zipfile.ZipFile(bundle, "w", compression=zipfile.ZIP_STORED) as zf:
            for out, name in zip(outputs, names, strict=True):
                zf.write(out.path, arcname=name)
        tf = TaskFile(
            task=task,
            role=TaskFile.Role.BUNDLE,
            original_name=f"universe-{task.tool}.zip",
            mime_type=ZIP_MIME,
            size_bytes=bundle.stat().st_size,
            position=len(outputs),
        )
        with bundle.open("rb") as fh:
            tf.file.save("bundle.zip", File(fh), save=False)
        tf.save()


def _delete_files(task: Task, role: str | None = None) -> None:
    qs = TaskFile.objects.filter(task=task)
    if role:
        qs = qs.filter(role=role)
    qs.delete()  # post_delete signal removes stored objects


def process_task(task_id: str, workdir: Path) -> None:
    """Run the tool for one task. Inputs are deleted as soon as processing ends."""
    claimed = Task.objects.filter(pk=task_id, status=Task.Status.QUEUED).update(status=Task.Status.PROCESSING)
    if not claimed:
        return  # already processed, failed or removed
    task = Task.objects.get(pk=task_id)
    tool = get_tool(task.tool)
    started = time.monotonic()
    error_code = ""
    try:
        if tool is None:
            raise ProcessingError("tool_unavailable")
        inputs = _materialize_inputs(task, tool, workdir)
        _scan_inputs(task, inputs)
        outputs = tool.run(inputs, task.options, workdir)
        # Not atomic on purpose: rows of partially stored outputs stay visible to the cleanup below.
        _store_outputs(task, outputs, workdir)
    except ProcessingError as exc:
        error_code = exc.code
    except Exception as exc:  # noqa: BLE001
        # Soft time limit arrives as an exception from Celery.
        error_code = "timeout" if type(exc).__name__ == "SoftTimeLimitExceeded" else "internal_error"
        if error_code == "internal_error":
            logger.exception("Conversion failed task=%s tool=%s", task.pk, task.tool)
    finally:
        _delete_files(task, TaskFile.Role.INPUT)

    if error_code:
        _delete_files(task, TaskFile.Role.OUTPUT)
        _delete_files(task, TaskFile.Role.BUNDLE)
    Task.objects.filter(pk=task.pk).update(
        status=Task.Status.FAILED if error_code else Task.Status.DONE,
        error_code=error_code,
        finished_at=timezone.now(),
        duration_ms=int((time.monotonic() - started) * 1000),
    )
    # The user may have pressed "delete now" while we were working.
    if Task.objects.filter(pk=task.pk, files_purged_at__isnull=False).exists():
        _delete_files(task)


def purge_task_files(task: Task) -> None:
    _delete_files(task)
    Task.objects.filter(pk=task.pk).update(files_purged_at=timezone.now())


def purge_expired(batch: int = 500) -> int:
    now = timezone.now()
    # Tasks stuck after a worker crash.
    Task.objects.filter(
        status__in=[Task.Status.QUEUED, Task.Status.PROCESSING], created_at__lt=now - timedelta(minutes=15)
    ).update(status=Task.Status.FAILED, error_code="timeout", finished_at=now)

    expired = list(
        Task.objects.filter(files_purged_at__isnull=True, expires_at__lte=now).order_by("expires_at")[:batch]
    )
    for task in expired:
        purge_task_files(task)
    Task.objects.filter(created_at__lt=now - timedelta(days=settings.TASK_HISTORY_DAYS)).delete()
    return len(expired)
