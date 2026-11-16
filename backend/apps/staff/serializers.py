from django.contrib.auth import get_user_model
from rest_framework import serializers

from apps.conversions.models import LimitPolicy, Task


class StaffUserSerializer(serializers.ModelSerializer):
    tasks_30d = serializers.IntegerField(read_only=True)
    has_password = serializers.SerializerMethodField()

    class Meta:
        model = get_user_model()
        fields = [
            "id",
            "email",
            "date_joined",
            "last_login",
            "is_active",
            "is_staff",
            "email_verified",
            "language",
            "has_password",
            "tasks_30d",
        ]

    def get_has_password(self, obj) -> bool:
        return obj.has_usable_password()


class FailedTaskSerializer(serializers.ModelSerializer):
    """Metadata only (F-73): no file names, no options a user typed, no owner identity."""

    class Meta:
        model = Task
        fields = ["id", "tool", "source", "error_code", "created_at", "duration_ms", "input_meta"]


class LimitPolicySerializer(serializers.ModelSerializer):
    max_file_mb = serializers.IntegerField(min_value=1, max_value=2048)
    max_total_mb = serializers.IntegerField(min_value=1, max_value=4096)
    daily_tasks = serializers.IntegerField(min_value=1, max_value=100_000)
    max_batch = serializers.IntegerField(min_value=1, max_value=200)
    retention_hours = serializers.IntegerField(min_value=1, max_value=24 * 30)

    class Meta:
        model = LimitPolicy
        fields = ["role", "max_file_mb", "max_total_mb", "daily_tasks", "max_batch", "retention_hours"]
        read_only_fields = ["role"]

    def validate(self, attrs: dict) -> dict:
        file_mb = attrs.get("max_file_mb", getattr(self.instance, "max_file_mb", 0))
        total_mb = attrs.get("max_total_mb", getattr(self.instance, "max_total_mb", 0))
        if total_mb < file_mb:
            raise serializers.ValidationError({"max_total_mb": ["Must be at least the per-file limit."]})
        return attrs
