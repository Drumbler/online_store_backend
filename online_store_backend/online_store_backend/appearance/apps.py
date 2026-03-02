"""Конфигурация Django-приложения внешнего вида."""

from django.apps import AppConfig


class AppearanceConfig(AppConfig):
    """Базовая конфигурация приложения appearance."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "online_store_backend.appearance"

    def ready(self):
        """Подключает signal-хендлеры после инициализации приложения."""
        from . import signals  # noqa: F401
