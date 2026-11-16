from django.db import migrations

# Defaults from docs/TZ.md section 5 (marked [Taxmin]); editable later in the admin.
POLICIES = [
    {"role": "guest", "max_file_mb": 50, "max_total_mb": 100, "daily_tasks": 20, "max_batch": 10,
     "retention_hours": 1, "daily_ocr_pages": 5},
    {"role": "registered", "max_file_mb": 200, "max_total_mb": 500, "daily_tasks": 100, "max_batch": 30,
     "retention_hours": 6, "daily_ocr_pages": 50},
]


def seed(apps, schema_editor):
    LimitPolicy = apps.get_model("conversions", "LimitPolicy")
    for row in POLICIES:
        LimitPolicy.objects.update_or_create(role=row["role"], defaults=row)


class Migration(migrations.Migration):
    dependencies = [("conversions", "0002_initial")]
    operations = [migrations.RunPython(seed, migrations.RunPython.noop)]
