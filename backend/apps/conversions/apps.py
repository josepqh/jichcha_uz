from django.apps import AppConfig


class ConversionsConfig(AppConfig):
    name = "apps.conversions"
    label = "conversions"

    def ready(self) -> None:
        import pillow_heif

        pillow_heif.register_heif_opener()
        from . import signals  # noqa: F401
