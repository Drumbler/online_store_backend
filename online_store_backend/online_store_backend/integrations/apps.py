"""Конфигурация Django-приложения интеграций."""

from django.apps import AppConfig


class IntegrationsConfig(AppConfig):
    """Регистрация приложения integrations в Django."""

    default_auto_field = "django.db.models.BigAutoField"
    name = "online_store_backend.integrations"
