from rest_framework import serializers

from .downloads import signed_download_url
from .models import Task, TaskFile


class TaskFileSerializer(serializers.ModelSerializer):
    name = serializers.CharField(source="original_name")
    size = serializers.IntegerField(source="size_bytes")
    mime = serializers.CharField(source="mime_type")
    download_url = serializers.SerializerMethodField()

    class Meta:
        model = TaskFile
        fields = ["id", "name", "size", "mime", "download_url"]

    def get_download_url(self, obj: TaskFile) -> str | None:
        if obj.role == TaskFile.Role.INPUT:
            return None
        return signed_download_url(obj.pk, obj.task.expires_at)


class TaskSerializer(serializers.ModelSerializer):
    options = serializers.SerializerMethodField()
    outputs = serializers.SerializerMethodField()
    bundle = serializers.SerializerMethodField()
    files_deleted = serializers.SerializerMethodField()

    class Meta:
        model = Task
        fields = [
            "id",
            "tool",
            "status",
            "error_code",
            "options",
            "created_at",
            "finished_at",
            "expires_at",
            "files_deleted",
            "outputs",
            "bundle",
        ]

    def _files(self, obj: Task, role: str) -> list[TaskFile]:
        # Uses the prefetched list; no extra query per task.
        return [f for f in obj.files.all() if f.role == role]

    def get_outputs(self, obj: Task) -> list[dict]:
        return TaskFileSerializer(self._files(obj, TaskFile.Role.OUTPUT), many=True).data

    def get_bundle(self, obj: Task) -> dict | None:
        bundle = self._files(obj, TaskFile.Role.BUNDLE)
        return TaskFileSerializer(bundle[0]).data if bundle else None

    def get_options(self, obj: Task) -> dict:
        # "_"-prefixed keys are server-side limits added at creation, not the user's choices.
        return {k: v for k, v in (obj.options or {}).items() if not k.startswith("_")}

    def get_files_deleted(self, obj: Task) -> bool:
        return obj.files_purged_at is not None
