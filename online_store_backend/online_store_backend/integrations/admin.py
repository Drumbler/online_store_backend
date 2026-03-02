"""Настройки Django admin для конфигурации интеграций."""

from django.contrib import admin

from .models import IntegrationConfig


@admin.register(IntegrationConfig)
class IntegrationConfigAdmin(admin.ModelAdmin):
    """Админка для включения и настройки провайдеров интеграций."""

    list_display = ("id", "kind", "provider_id", "enabled", "is_sandbox", "updated_at")
    list_filter = ("kind", "enabled", "is_sandbox")
    search_fields = ("provider_id", "display_name")
