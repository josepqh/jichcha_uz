import logging

from django.db.models.signals import post_delete
from django.dispatch import receiver

from .models import TaskFile

logger = logging.getLogger(__name__)


@receiver(post_delete, sender=TaskFile)
def delete_stored_file(sender, instance: TaskFile, **kwargs) -> None:
    """Remove the object from storage whenever its row goes (purge, user delete, account delete)."""
    if not instance.file:
        return
    try:
        instance.file.delete(save=False)
    except Exception:  # noqa: BLE001 - storage outage must not break deletion of metadata
        logger.exception("Failed to delete stored file for task_file=%s", instance.pk)
