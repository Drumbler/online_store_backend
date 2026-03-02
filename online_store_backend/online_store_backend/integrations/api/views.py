"""Админ API для управления интеграциями оплаты и доставки."""

from __future__ import annotations

from django.http import Http404
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import IntegrationConfig
from ..models import IntegrationKind
from ..providers import get_payment_providers
from ..providers import get_shipping_providers


class IntegrationConfigUpsertSerializer(serializers.Serializer):
    """Валидатор обновления конфигурации интеграции."""

    enabled = serializers.BooleanField(required=False)
    is_sandbox = serializers.BooleanField(required=False)
    display_name = serializers.CharField(required=False, allow_blank=True)
    credentials = serializers.DictField(required=False)
    settings = serializers.DictField(required=False)


def _providers_by_kind(kind: str):
    """Вернуть реестр провайдеров по типу интеграции."""
    if kind == IntegrationKind.PAYMENT:
        return get_payment_providers()
    if kind == IntegrationKind.SHIPPING:
        return get_shipping_providers()
    raise Http404


def _get_provider(kind: str, provider_id: str):
    """Найти конкретный провайдер в соответствующем реестре."""
    providers = _providers_by_kind(kind)
    provider = providers.get(provider_id)
    if not provider:
        raise Http404
    return provider


def _password_fields_map(fields_schema: list[dict]):
    """Построить карту секретных полей (credentials/settings) по schema провайдера."""
    result = {"credentials": set(), "settings": set()}
    for field in fields_schema:
        if field.get("type") != "password":
            continue
        group = field.get("group") or "credentials"
        name = field.get("name")
        if group in result and name:
            result[group].add(name)
    return result


def _masked_payload(kind: str, provider, config: IntegrationConfig | None):
    """Подготовить payload конфигурации, скрывая секретные значения."""
    fields_schema = provider.fields_schema()
    password_fields = _password_fields_map(fields_schema)
    raw_credentials = (config.credentials if config else {}) or {}
    raw_settings = (config.settings if config else {}) or {}

    credentials = dict(raw_credentials)
    settings = dict(raw_settings)

    for name in password_fields["credentials"]:
        if name in credentials and credentials.get(name) not in (None, ""):
            credentials[name] = "******"
    for name in password_fields["settings"]:
        if name in settings and settings.get(name) not in (None, ""):
            settings[name] = "******"

    return {
        "id": config.id if config else None,
        "kind": config.kind if config else kind,
        "provider_id": provider.id,
        "enabled": config.enabled if config else False,
        "is_sandbox": config.is_sandbox if config else True,
        "display_name": config.display_name if config else "",
        "credentials": credentials,
        "settings": settings,
    }


def _apply_secret_placeholders(existing: dict, incoming: dict, password_fields: set[str]):
    """Слить входные поля с текущими, сохраняя секреты при плейсхолдере `******`."""
    merged = dict(existing)
    for key, value in incoming.items():
        if key in password_fields and value == "******":
            # Keep currently stored secret.
            continue
        merged[key] = value
    return merged


def _validate_required_fields(enabled: bool, fields_schema: list[dict], credentials: dict, settings: dict):
    """Проверить обязательные поля конфигурации только для включенной интеграции."""
    if not enabled:
        return

    errors: dict[str, list[str]] = {}
    for field in fields_schema:
        if not field.get("required"):
            continue
        group = field.get("group") or "credentials"
        name = field.get("name")
        if not name:
            continue
        source = credentials if group == "credentials" else settings
        value = source.get(name)
        if value in (None, ""):
            errors[f"{group}.{name}"] = ["Required"]
    if errors:
        raise serializers.ValidationError(errors)


class AdminIntegrationsProvidersView(APIView):
    """Справочник всех доступных провайдеров интеграций."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Вернуть описание провайдеров оплаты и доставки."""
        payment = [
            {
                "id": adapter.id,
                "title": adapter.title,
                "description": adapter.description,
                "fields_schema": adapter.fields_schema(),
            }
            for adapter in get_payment_providers().values()
        ]
        shipping = [
            {
                "id": adapter.id,
                "title": adapter.title,
                "description": adapter.description,
                "fields_schema": adapter.fields_schema(),
            }
            for adapter in get_shipping_providers().values()
        ]
        return Response({"payment": payment, "shipping": shipping}, status=status.HTTP_200_OK)


class AdminIntegrationConfigView(APIView):
    """Получение и обновление конфигурации конкретной интеграции."""

    permission_classes = [IsAdminUser]

    def get(self, request, kind, provider_id):
        """Прочитать текущую конфигурацию интеграции с маскированием секретов."""
        provider = _get_provider(kind, provider_id)
        config = IntegrationConfig.objects.filter(kind=kind, provider_id=provider_id).first()
        payload = _masked_payload(kind, provider, config)
        return Response(payload, status=status.HTTP_200_OK)

    def put(self, request, kind, provider_id):
        """Создать/обновить конфигурацию интеграции и провалидировать обязательные поля."""
        provider = _get_provider(kind, provider_id)
        serializer = IntegrationConfigUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        config, _ = IntegrationConfig.objects.get_or_create(
            kind=kind,
            provider_id=provider_id,
            defaults={
                "enabled": False,
                "is_sandbox": True,
                "display_name": "",
                "credentials": {},
                "settings": {},
            },
        )

        fields_schema = provider.fields_schema()
        password_map = _password_fields_map(fields_schema)

        incoming_credentials = data.get("credentials", {}) or {}
        incoming_settings = data.get("settings", {}) or {}

        config.credentials = _apply_secret_placeholders(
            config.credentials or {},
            incoming_credentials,
            password_map["credentials"],
        )
        config.settings = _apply_secret_placeholders(
            config.settings or {},
            incoming_settings,
            password_map["settings"],
        )

        if "enabled" in data:
            config.enabled = data["enabled"]
        if "is_sandbox" in data:
            config.is_sandbox = data["is_sandbox"]
        if "display_name" in data:
            config.display_name = data["display_name"]

        _validate_required_fields(
            enabled=config.enabled,
            fields_schema=fields_schema,
            credentials=config.credentials or {},
            settings=config.settings or {},
        )

        config.save()
        payload = _masked_payload(kind, provider, config)
        return Response(payload, status=status.HTTP_200_OK)


class AdminIntegrationTestConnectionView(APIView):
    """Запуск теста подключения для выбранного провайдера интеграции."""

    permission_classes = [IsAdminUser]

    def post(self, request, kind, provider_id):
        """Проверить доступность внешнего провайдера с текущей конфигурацией."""
        provider = _get_provider(kind, provider_id)
        config = IntegrationConfig.objects.filter(kind=kind, provider_id=provider_id).first()
        if config is None:
            config = IntegrationConfig(
                kind=kind,
                provider_id=provider_id,
                enabled=False,
                is_sandbox=True,
                display_name="",
                credentials={},
                settings={},
            )
        ok, message = provider.test_connection(config)
        return Response({"ok": bool(ok), "message": str(message)}, status=status.HTTP_200_OK)
