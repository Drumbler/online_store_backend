from decimal import Decimal

import pytest
import requests
from rest_framework.test import APIClient

from online_store_backend.cart.models import Cart
from online_store_backend.cart.models import CartItem
from online_store_backend.cart.models import CartStatus
from online_store_backend.integrations.models import IntegrationConfig
from online_store_backend.integrations.models import IntegrationKind


@pytest.fixture
def api_client():
    return APIClient()


class _MockResponse:
    def __init__(self, status_code: int, payload: dict):
        self.status_code = status_code
        self._payload = payload
        self.content = b"{}"

    def json(self):
        return self._payload


def _prepare_guest_cart(client: APIClient):
    session = client.session
    session.save()
    cart = Cart.objects.create(session_key=session.session_key, status=CartStatus.ACTIVE)
    CartItem.objects.create(
        cart=cart,
        product_id="p-1",
        product_title_snapshot="Snapshot",
        unit_price_snapshot=Decimal("1000.00"),
        currency_snapshot="RUB",
        image_url_snapshot="",
        quantity=1,
    )
    return cart


@pytest.mark.django_db
def test_yandex_ndd_pickup_points_endpoint_returns_normalized_results(api_client, monkeypatch):
    IntegrationConfig.objects.create(
        kind=IntegrationKind.SHIPPING,
        provider_id="yandex_ndd",
        enabled=True,
        settings={"use_public_test_token": True},
    )

    def _mock_post(url, json, headers, timeout):
        assert url.endswith("/api/b2b/platform/pickup-points/list")
        return _MockResponse(
            200,
            {
                "points": [
                    {
                        "id": "PVZ-1",
                        "name": "Pickup #1",
                        "address": {"full_address": "Moscow, Lenina 1", "locality": "Moscow"},
                        "position": {"latitude": 55.751, "longitude": 37.618},
                        "type": "pickup_point",
                    },
                    {
                        "id": "PVZ-2",
                        "name": "Pickup #2",
                        "address": {"full_address": "Moscow, Tverskaya 2", "locality": "Moscow"},
                        "position": {"latitude": 55.761, "longitude": 37.628},
                        "type": "pickup_point",
                    },
                ]
            },
        )

    monkeypatch.setattr("online_store_backend.integrations.providers.requests.post", _mock_post)

    response = api_client.get("/api/shipping/yandex_ndd/pickup-points/?city=Moscow&q=Lenina")

    assert response.status_code == 200
    payload = response.json()
    assert "results" in payload
    assert len(payload["results"]) == 1
    assert payload["results"][0]["id"] == "PVZ-1"
    assert payload["results"][0]["address"] == "Moscow, Lenina 1"


@pytest.mark.django_db
def test_yandex_ndd_quote_endpoint_returns_offers(api_client, monkeypatch):
    _prepare_guest_cart(api_client)
    IntegrationConfig.objects.create(
        kind=IntegrationKind.SHIPPING,
        provider_id="yandex_ndd",
        enabled=True,
        settings={"use_public_test_token": True},
    )

    monkeypatch.setattr(
        "online_store_backend.orders.api.checkout_views.get_product",
        lambda _product_id: {
            "id": "p-1",
            "title": "Product 1",
            "price": "1000.00",
            "discount_percent": 0,
            "currency": "RUB",
            "image_url": "",
        },
    )

    def _mock_post(url, json, headers, timeout):
        assert url.endswith("/api/b2b/platform/offers/create")
        assert isinstance(json.get("billing_info"), dict)
        assert json["billing_info"].get("payment_method") == "already_paid"
        assert isinstance(json.get("recipient_info"), dict)
        assert isinstance(json.get("items"), list) and json["items"]
        assert isinstance(json.get("places"), list) and json["places"]
        return _MockResponse(
            200,
            {
                "offers": [
                    {
                        "offer_id": "offer-1",
                        "offer_details": {
                            "pricing_total": "350 RUB",
                            "delivery_interval": {
                                "policy": "time_interval",
                                "min": "2026-03-01T10:00:00+03:00",
                                "max": "2026-03-01T14:00:00+03:00",
                            },
                        },
                    }
                ]
            },
        )

    monkeypatch.setattr("online_store_backend.integrations.providers.requests.post", _mock_post)

    response = api_client.post(
        "/api/shipping/yandex_ndd/quote/",
        {
            "address": {
                "city": "Moscow",
                "postal_code": "101000",
                "street": "Tverskaya",
                "house": "1",
            },
            "shipping_type": "courier",
        },
        format="json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert "offers" in payload
    assert len(payload["offers"]) == 1
    assert payload["offers"][0]["id"] == "offer-1"
    assert payload["offers"][0]["price"] == 350.0


@pytest.mark.django_db
def test_yandex_ndd_pickup_points_returns_502_when_provider_unreachable(api_client, monkeypatch):
    IntegrationConfig.objects.create(
        kind=IntegrationKind.SHIPPING,
        provider_id="yandex_ndd",
        enabled=True,
        settings={"use_public_test_token": True},
    )

    def _mock_post(url, json, headers, timeout):
        raise requests.RequestException("connection failed")

    monkeypatch.setattr("online_store_backend.integrations.providers.requests.post", _mock_post)

    response = api_client.get("/api/shipping/yandex_ndd/pickup-points/?city=Moscow")

    assert response.status_code == 502
