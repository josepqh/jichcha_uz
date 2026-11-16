from django.contrib import admin

from .models import LimitPolicy, Task, TaskFile, UsageCounter


@admin.register(LimitPolicy)
class LimitPolicyAdmin(admin.ModelAdmin):
    list_display = ("role", "max_file_mb", "max_total_mb", "daily_tasks", "max_batch", "retention_hours")


class TaskFileInline(admin.TabularInline):
    model = TaskFile
    # File contents are never exposed in admin; only metadata.
    fields = ("role", "original_name", "mime_type", "size_bytes")
    readonly_fields = fields
    extra = 0
    can_delete = False


@admin.register(Task)
class TaskAdmin(admin.ModelAdmin):
    list_display = ("id", "tool", "status", "error_code", "user", "duration_ms", "created_at")
    list_filter = ("status", "tool", "error_code")
    search_fields = ("id", "user__email")
    readonly_fields = [f.name for f in Task._meta.fields]
    inlines = [TaskFileInline]
    list_select_related = ("user",)

    def has_add_permission(self, request):
        return False


@admin.register(UsageCounter)
class UsageCounterAdmin(admin.ModelAdmin):
    list_display = ("subject", "day", "tasks_count", "bytes_processed")
    list_filter = ("day",)
