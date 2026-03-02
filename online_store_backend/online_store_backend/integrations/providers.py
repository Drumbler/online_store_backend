"""Адаптеры платежных и логистических интеграций магазина."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from decimal import InvalidOperation
import logging
import random
import re
from urllib.parse import urlencode
from uuid import uuid4

import requests
from django.conf import settings

from .models import IntegrationConfig

logger = logging.getLogger(__name__)

YANDEX_NDD_PUBLIC_TEST_TOKEN = "y1_AgAAAAA6tEATAnx87wAAAWQcbM8Bll8VQ6Dr2dlWAAmh7_ci6TxhXw"
YANDEX_NDD_INT32_MAX = 2_147_483_647


@dataclass
class BaseProviderAdapter:
    """Базовые метаданные любого провайдера интеграции."""

    id: str
    title: str
    description: str = ""

    def fields_schema(self) -> list[dict]:
        """Возвращает схему полей настройки провайдера."""
        return []


class PaymentProviderUnavailableError(Exception):
    """Raised when payment provider is temporarily unreachable."""


class ShippingProviderUnavailableError(Exception):
    """Raised when shipping provider is temporarily unreachable."""


class ShippingProviderResponseError(Exception):
    """Raised when shipping provider returns unexpected payload."""


class PaymentProviderAdapter(BaseProviderAdapter):
    """Базовый интерфейс адаптера платежного провайдера."""

    def test_connection(self, config: IntegrationConfig) -> tuple[bool, str]:
        """Проверяет доступность провайдера по текущей конфигурации."""
        raise NotImplementedError

    def create_payment(
        self,
        order,
        config: IntegrationConfig,
        return_url: str,
    ) -> dict:
        """Создает внешнюю платежную сессию для заказа."""
        raise NotImplementedError


class ShippingProviderAdapter(BaseProviderAdapter):
    """Базовый интерфейс адаптера службы доставки."""

    def test_connection(self, config: IntegrationConfig) -> tuple[bool, str]:
        """Проверяет доступность службы доставки."""
        raise NotImplementedError

    def quote(
        self,
        order_data: dict,
        address: dict,
        shipping_type: str,
        pickup_point_id: str | None,
        config: IntegrationConfig,
    ) -> dict:
        """Рассчитывает стоимость и доступные офферы доставки."""
        raise NotImplementedError

    def get_pickup_points(self, city: str, query: str | None = None) -> list[dict]:
        """Возвращает список доступных ПВЗ для выбранного города."""
        return []


class DemoPaymentProviderAdapter(PaymentProviderAdapter):
    """Демо-адаптер оплаты для локальной разработки и тестов."""

    id = "demo"
    title = "Demo payment"
    description = "Local demo adapter for payment integration wiring."

    def fields_schema(self) -> list[dict]:
        return [
            {
                "name": "api_key",
                "label": "API key",
                "type": "password",
                "required": False,
                "group": "credentials",
            },
            {
                "name": "merchant_id",
                "label": "Merchant ID",
                "type": "text",
                "required": False,
                "group": "credentials",
            },
        ]

    def test_connection(self, config: IntegrationConfig) -> tuple[bool, str]:
        api_key = (config.credentials or {}).get("api_key")
        if api_key == "bad":
            return False, "Demo payment: invalid API key."
        return True, "Demo payment connection OK."

    def create_payment(self, order, config: IntegrationConfig, return_url: str) -> dict:
        external_id = uuid4().hex
        query = urlencode(
            {
                "external_id": external_id,
                "order_number": str(order.id),
                "provider_id": self.id,
            }
        )
        return {
            "payment_url": f"{return_url}?{query}",
            "external_id": external_id,
        }


class DemoShippingProviderAdapter(ShippingProviderAdapter):
    """Демо-адаптер доставки с локальными тестовыми ПВЗ."""

    id = "demo"
    title = "Demo shipping"
    description = "Local demo adapter for shipping integration wiring."

    def fields_schema(self) -> list[dict]:
        return [
            {
                "name": "api_key",
                "label": "API key",
                "type": "password",
                "required": False,
                "group": "credentials",
            }
        ]

    def test_connection(self, config: IntegrationConfig) -> tuple[bool, str]:
        api_key = (config.credentials or {}).get("api_key")
        if api_key == "bad":
            return False, "Demo shipping: invalid API key."
        return True, "Demo shipping connection OK."

    def quote(
        self,
        order_data: dict,
        address: dict,
        shipping_type: str,
        pickup_point_id: str | None,
        config: IntegrationConfig,
    ) -> dict:
        return {
            "shipping_price": 300,
            "eta": "2-4 days",
            "currency": "RUB",
            "offers": [
                {
                    "id": "DEMO-OFFER-1",
                    "delivery_type": shipping_type,
                    "price": 300,
                    "date_interval": {"from": None, "to": None},
                }
            ],
        }

    def get_pickup_points(self, city: str, query: str | None = None) -> list[dict]:
        points_pool = [
            {
                "id": "DEMO-MSK-1",
                "title": "Demo PVZ Tverskaya",
                "address": "Москва, Тверская улица, 7",
                "lat": 55.7578,
                "lng": 37.6130,
                "type": "pvz",
                "work_time": "10-22",
            },
            {
                "id": "DEMO-MSK-2",
                "title": "Demo PVZ Arbat",
                "address": "Москва, улица Арбат, 12",
                "lat": 55.7516,
                "lng": 37.5924,
                "type": "pvz",
                "work_time": "10-21",
            },
            {
                "id": "DEMO-MSK-3",
                "title": "Demo PVZ Chistye Prudy",
                "address": "Москва, Мясницкая улица, 24",
                "lat": 55.7645,
                "lng": 37.6376,
                "type": "pvz",
                "work_time": "9-21",
            },
            {
                "id": "DEMO-MSK-4",
                "title": "Demo PVZ Belorusskaya",
                "address": "Москва, Лесная улица, 5",
                "lat": 55.7774,
                "lng": 37.5873,
                "type": "pvz",
                "work_time": "9-21",
            },
            {
                "id": "DEMO-MSK-5",
                "title": "Demo PVZ Kurskaya",
                "address": "Москва, Земляной Вал, 33",
                "lat": 55.7571,
                "lng": 37.6593,
                "type": "pvz",
                "work_time": "10-22",
            },
            {
                "id": "DEMO-MSK-6",
                "title": "Demo PVZ Sokolniki",
                "address": "Москва, Русаковская улица, 22",
                "lat": 55.7939,
                "lng": 37.6792,
                "type": "pvz",
                "work_time": "9-20",
            },
            {
                "id": "DEMO-MSK-7",
                "title": "Demo PVZ Taganskaya",
                "address": "Москва, Таганская улица, 29",
                "lat": 55.7402,
                "lng": 37.6589,
                "type": "pvz",
                "work_time": "9-21",
            },
            {
                "id": "DEMO-MSK-8",
                "title": "Demo PVZ Prospekt Mira",
                "address": "Москва, проспект Мира, 47",
                "lat": 55.7814,
                "lng": 37.6335,
                "type": "pvz",
                "work_time": "10-22",
            },
        ]
        query_text = (query or "").strip().lower()
        if query_text:
            points_pool = [
                point
                for point in points_pool
                if query_text in f"{point.get('title', '')} {point.get('address', '')}".lower()
            ]
        if len(points_pool) <= 3:
            return points_pool
        return random.sample(points_pool, 3)


class YandexNddShippingProviderAdapter(ShippingProviderAdapter):
    """Адаптер расчета доставки через Yandex NDD API."""

    id = "yandex_ndd"
    title = "Yandex Delivery (NDD test)"
    description = "Yandex Other-day API integration for test contour (Moscow)."

    def fields_schema(self) -> list[dict]:
        return [
            {
                "name": "token",
                "label": "Bearer token",
                "type": "password",
                "required": False,
                "group": "credentials",
            },
            {
                "name": "base_url",
                "label": "Base URL",
                "type": "text",
                "required": False,
                "group": "settings",
            },
            {
                "name": "platform_station_id",
                "label": "Platform station ID",
                "type": "text",
                "required": False,
                "group": "settings",
            },
            {
                "name": "use_public_test_token",
                "label": "Use Yandex public test token",
                "type": "boolean",
                "required": False,
                "group": "settings",
            },
        ]

    def _resolve_token(self, config: IntegrationConfig) -> str:
        credentials = (config.credentials or {}) if config else {}
        token = str(credentials.get("token") or "").strip()
        if token:
            return token

        settings_token = str(getattr(settings, "YANDEX_NDD_TOKEN", "") or "").strip()
        if settings_token:
            return settings_token

        settings_data = (config.settings or {}) if config else {}
        use_public_test_token = bool(settings_data.get("use_public_test_token", bool(config.is_sandbox)))
        if use_public_test_token:
            return YANDEX_NDD_PUBLIC_TEST_TOKEN

        raise ShippingProviderResponseError("Yandex NDD token is not configured.")

    def _resolve_base_url(self, config: IntegrationConfig) -> str:
        settings_data = (config.settings or {}) if config else {}
        base_url = str(settings_data.get("base_url") or getattr(settings, "YANDEX_NDD_BASE_URL", "")).strip()
        if not base_url:
            raise ShippingProviderResponseError("Yandex NDD base URL is not configured.")
        return base_url.rstrip("/")

    def _resolve_platform_station_id(self, config: IntegrationConfig) -> str:
        settings_data = (config.settings or {}) if config else {}
        platform_station_id = str(
            settings_data.get("platform_station_id") or getattr(settings, "YANDEX_NDD_PLATFORM_STATION_ID", "")
        ).strip()
        if not platform_station_id:
            raise ShippingProviderResponseError("Yandex NDD platform_station_id is not configured.")
        return platform_station_id

    def _request_json(self, config: IntegrationConfig, path: str, payload: dict) -> dict:
        url = f"{self._resolve_base_url(config)}{path}"
        headers = {
            "Authorization": f"Bearer {self._resolve_token(config)}",
            "Content-Type": "application/json",
        }
        timeout = int(getattr(settings, "YANDEX_NDD_TIMEOUT_SECONDS", 10))

        try:
            response = requests.post(url, json=payload, headers=headers, timeout=timeout)
        except requests.RequestException as exc:
            logger.warning("Yandex NDD request failed: %s", exc)
            raise ShippingProviderUnavailableError("Yandex NDD is unreachable.") from exc

        if response.status_code >= 500:
            logger.warning("Yandex NDD server error status=%s", response.status_code)
            raise ShippingProviderUnavailableError("Yandex NDD is temporarily unavailable.")

        if response.status_code >= 400:
            payload = None
            try:
                payload = response.json() if response.content else {}
            except ValueError:
                payload = None

            detail = ""
            if isinstance(payload, dict):
                code = str(payload.get("code") or "").strip()
                message = payload.get("message") or payload.get("detail") or ""
                message = str(message).strip()
                if code and message:
                    detail = f"{code}: {message}"
                else:
                    detail = code or message
            if not detail:
                detail = str(response.text or "").strip()
            if len(detail) > 350:
                detail = f"{detail[:350]}..."

            logger.warning(
                "Yandex NDD request error status=%s path=%s detail=%s",
                response.status_code,
                path,
                detail or "<empty>",
            )
            if detail:
                raise ShippingProviderResponseError(
                    f"Yandex NDD request failed with status {response.status_code}: {detail}"
                )
            raise ShippingProviderResponseError(f"Yandex NDD request failed with status {response.status_code}.")

        try:
            data = response.json() if response.content else {}
        except ValueError as exc:
            logger.warning("Yandex NDD returned invalid JSON")
            raise ShippingProviderResponseError("Yandex NDD returned invalid JSON.") from exc

        if not isinstance(data, dict):
            raise ShippingProviderResponseError("Yandex NDD returned invalid payload.")

        return data

    @staticmethod
    def _to_float(value):
        if isinstance(value, (int, float)):
            return float(value)
        if isinstance(value, str):
            match = re.search(r"-?\d+(?:[.,]\d+)?", value)
            if match:
                return float(match.group(0).replace(",", "."))
        return None

    @staticmethod
    def _build_full_address(address: dict) -> str:
        if not isinstance(address, dict):
            return ""
        parts = [
            str(address.get("city") or "").strip(),
            str(address.get("street") or "").strip(),
            str(address.get("house") or "").strip(),
        ]
        return ", ".join(part for part in parts if part)

    @staticmethod
    def _to_minor_units(value: object, default_minor: int) -> int:
        if value in (None, ""):
            return default_minor
        try:
            amount = Decimal(str(value))
        except (InvalidOperation, TypeError, ValueError):
            return default_minor
        if amount < 0:
            return default_minor
        minor = int((amount * Decimal("100")).quantize(Decimal("1")))
        return max(1, min(minor, YANDEX_NDD_INT32_MAX))

    def _normalize_pickup_point(self, point: dict):
        if not isinstance(point, dict):
            return None

        point_id = point.get("platform_station_id") or point.get("point_id") or point.get("id")
        if point_id in (None, ""):
            return None

        address_obj = point.get("address") if isinstance(point.get("address"), dict) else {}
        address_text = None
        if isinstance(point.get("address"), str):
            address_text = point.get("address")
        if not address_text:
            address_text = (
                address_obj.get("full_address")
                or address_obj.get("address")
                or point.get("full_address")
                or point.get("address_text")
                or ""
            )

        position = point.get("position") if isinstance(point.get("position"), dict) else {}
        lat = self._to_float(point.get("lat") or point.get("latitude") or position.get("latitude"))
        lng = self._to_float(point.get("lng") or point.get("longitude") or position.get("longitude"))

        return {
            "id": str(point_id),
            "title": point.get("name") or point.get("title") or f"Pickup point {point_id}",
            "address": str(address_text or "").strip(),
            "lat": lat,
            "lng": lng,
            "type": point.get("type") or "pvz",
        }

    def get_pickup_points(self, city: str, query: str | None = None, config: IntegrationConfig | None = None) -> list[dict]:
        if config is None:
            config = IntegrationConfig(kind="shipping", provider_id=self.id, settings={"use_public_test_token": True})

        payload = self._request_json(config, "/api/b2b/platform/pickup-points/list", {})
        raw_points = payload.get("points")
        if not isinstance(raw_points, list):
            raw_points = []

        normalized = []
        city_lc = (city or "").strip().lower()
        query_lc = (query or "").strip().lower()

        for point in raw_points:
            mapped = self._normalize_pickup_point(point)
            if not mapped:
                continue

            if city_lc:
                locality = ""
                if isinstance(point, dict):
                    address_obj = point.get("address") if isinstance(point.get("address"), dict) else {}
                    locality = str(address_obj.get("locality") or point.get("city") or "").lower()
                haystack_city = f"{locality} {(mapped.get('address') or '').lower()}"
                if locality and city_lc not in haystack_city:
                    continue

            if query_lc:
                haystack = f"{mapped.get('title', '')} {mapped.get('address', '')}".lower()
                if query_lc not in haystack:
                    continue

            normalized.append(mapped)

        return normalized

    def _normalize_offers(self, payload: dict, shipping_type: str) -> list[dict]:
        raw_offers = payload.get("offers")
        if not isinstance(raw_offers, list):
            return []

        normalized = []
        for offer in raw_offers:
            if not isinstance(offer, dict):
                continue
            details = offer.get("offer_details") if isinstance(offer.get("offer_details"), dict) else {}
            delivery_interval = details.get("delivery_interval") if isinstance(details.get("delivery_interval"), dict) else {}
            pickup_interval = details.get("pickup_interval") if isinstance(details.get("pickup_interval"), dict) else {}
            interval = pickup_interval or delivery_interval

            delivery_type = shipping_type
            if delivery_interval.get("policy") == "self_pickup":
                delivery_type = "pickup"

            price_raw = details.get("pricing_total") or details.get("pricing") or offer.get("price")
            price = self._to_float(price_raw)

            normalized.append(
                {
                    "id": str(offer.get("offer_id") or offer.get("id") or uuid4().hex),
                    "delivery_type": delivery_type,
                    "price": price,
                    "date_interval": {
                        "from": interval.get("min"),
                        "to": interval.get("max"),
                    },
                }
            )

        return normalized

    def quote(
        self,
        order_data: dict,
        address: dict,
        shipping_type: str,
        pickup_point_id: str | None,
        config: IntegrationConfig,
    ) -> dict:
        source_platform_station_id = self._resolve_platform_station_id(config)
        operator_request_id = f"checkout-{uuid4().hex[:16]}"
        items_count = max(1, int(order_data.get("items_count") or 1))
        items_total_minor = self._to_minor_units(order_data.get("items_total"), default_minor=10000)
        unit_price_minor = max(1, min(items_total_minor // items_count, YANDEX_NDD_INT32_MAX))
        place_barcode = f"place-{operator_request_id}"
        city = str(address.get("city") or "").strip()
        full_address = self._build_full_address(address)

        destination: dict
        if shipping_type == "pickup":
            if not pickup_point_id:
                raise ShippingProviderResponseError("pickup_point_id is required for pickup quote.")
            destination = {
                "type": "platform_station",
                "platform_station": {
                    "platform_id": str(pickup_point_id),
                },
            }
        else:
            if not full_address:
                raise ShippingProviderResponseError("Address is required for courier quote.")
            destination = {
                "type": "custom_location",
                "custom_location": {
                    "details": {
                        "full_address": full_address,
                        "locality": city,
                    }
                },
            }

        payload = {
            "info": {
                "operator_request_id": operator_request_id,
            },
            "source": {
                "platform_station": {
                    "platform_id": source_platform_station_id,
                }
            },
            "destination": destination,
            "billing_info": {
                "payment_method": "already_paid",
                "delivery_cost": 0,
            },
            "recipient_info": {
                "first_name": "Customer",
                "phone": "+79990000000",
                "email": "customer@example.com",
            },
            "items": [
                {
                    "name": "Order items",
                    "count": items_count,
                    "article": operator_request_id,
                    "place_barcode": place_barcode,
                    "billing_details": {
                        "unit_price": unit_price_minor,
                        "assessed_unit_price": unit_price_minor,
                    },
                    "physical_dims": {
                        "weight_gross": 1000,
                        "dx": 20,
                        "dy": 20,
                        "dz": 10,
                    },
                }
            ],
            "places": [
                {
                    "barcode": place_barcode,
                    "physical_dims": {
                        "weight_gross": 1000,
                        "dx": 20,
                        "dy": 20,
                        "dz": 10,
                    },
                }
            ],
        }

        response_payload = self._request_json(config, "/api/b2b/platform/offers/create", payload)
        offers = self._normalize_offers(response_payload, shipping_type)
        if not offers:
            raise ShippingProviderResponseError("Yandex NDD returned no delivery offers.")

        prices = [offer.get("price") for offer in offers if isinstance(offer.get("price"), (int, float))]
        if not prices:
            raise ShippingProviderResponseError("Yandex NDD offers do not contain price.")

        shipping_price = min(prices)
        return {
            "shipping_price": shipping_price,
            "currency": "RUB",
            "offers": offers,
        }

    def test_connection(self, config: IntegrationConfig) -> tuple[bool, str]:
        try:
            self.get_pickup_points(city="Moscow", query="", config=config)
        except ShippingProviderUnavailableError:
            return False, "Yandex NDD is unreachable."
        except ShippingProviderResponseError as exc:
            return False, str(exc)
        return True, "Yandex NDD connection OK."


_PAYMENT_PROVIDERS = {
    DemoPaymentProviderAdapter.id: DemoPaymentProviderAdapter(
        id=DemoPaymentProviderAdapter.id,
        title=DemoPaymentProviderAdapter.title,
        description=DemoPaymentProviderAdapter.description,
    )
}

_SHIPPING_PROVIDERS = {
    DemoShippingProviderAdapter.id: DemoShippingProviderAdapter(
        id=DemoShippingProviderAdapter.id,
        title=DemoShippingProviderAdapter.title,
        description=DemoShippingProviderAdapter.description,
    ),
    YandexNddShippingProviderAdapter.id: YandexNddShippingProviderAdapter(
        id=YandexNddShippingProviderAdapter.id,
        title=YandexNddShippingProviderAdapter.title,
        description=YandexNddShippingProviderAdapter.description,
    ),
}


def get_payment_providers() -> dict[str, PaymentProviderAdapter]:
    """Возвращает реестр доступных платежных провайдеров."""
    return _PAYMENT_PROVIDERS


def get_shipping_providers() -> dict[str, ShippingProviderAdapter]:
    """Возвращает реестр доступных провайдеров доставки."""
    return _SHIPPING_PROVIDERS
