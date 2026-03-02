"""Модели для хранения конфигурации внешних интеграций."""

from django.db import models


class IntegrationKind(models.TextChoices):
    """Типы интеграций, доступные в проекте."""

    PAYMENT = "payment", "Payment"
    SHIPPING = "shipping", "Shipping"


class IntegrationConfig(models.Model):
    """Параметры подключения и режим работы конкретного провайдера."""

    kind = models.CharField(max_length=32, choices=IntegrationKind.choices)
    provider_id = models.CharField(max_length=64)
    enabled = models.BooleanField(default=False)
    is_sandbox = models.BooleanField(default=True)
    display_name = models.CharField(max_length=255, blank=True, default="")
    credentials = models.JSONField(default=dict, blank=True)
    settings = models.JSONField(default=dict, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["kind", "provider_id"],
                name="uniq_kind_provider",
            )
        ]

    def __str__(self) -> str:
        return f"IntegrationConfig({self.kind}:{self.provider_id})"
