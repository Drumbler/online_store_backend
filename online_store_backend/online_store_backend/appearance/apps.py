from django.apps import AppConfig


class AppearanceConfig(AppConfig):
    default_auto_field = "django.db.models.BigAutoField"
    name = "online_store_backend.appearance"

    def ready(self):
        from . import signals  # noqa: F401
