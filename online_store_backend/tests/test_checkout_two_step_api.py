from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from online_store_backend.cart.models import Cart
from online_store_backend.cart.models import CartItem
from online_store_backend.cart.models import CartStatus
from online_store_backend.integrations.models import IntegrationConfig
from online_store_backend.integrations.models import IntegrationKind
from online_store_backend.orders.models import Order
from online_store_backend.orders.models import OrderStatus


@pytest.fixture
def api_client():
    return APIClient()


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
        quantity=2,
    )
    return cart


@pytest.mark.django_db
def test_checkout_preview_returns_totals_without_creating_order(api_client, monkeypatch):
    _prepare_guest_cart(api_client)
    IntegrationConfig.objects.create(
        kind=IntegrationKind.SHIPPING,
        provider_id="demo",
        enabled=True,
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

    response = api_client.post(
        "/api/checkout/preview/",
        {
            "address": {
                "city": "Ekaterinburg",
                "postal_code": "620000",
                "street": "Lenina",
                "house": "1",
            },
            "shipping_provider": "demo",
            "shipping_type": "courier",
        },
        format="json",
    )

    assert response.status_code == 200
    payload = response.json()
    assert payload["items_total"] == 2000.0
    assert payload["shipping_price"] == 300.0
    assert payload["total"] == 2300.0
    assert Order.objects.count() == 0


@pytest.mark.django_db
def test_checkout_confirm_creates_pending_payment_order_and_clears_cart(api_client, monkeypatch):
    cart = _prepare_guest_cart(api_client)
    IntegrationConfig.objects.create(
        kind=IntegrationKind.SHIPPING,
        provider_id="demo",
        enabled=True,
    )

    monkeypatch.setattr(
        "online_store_backend.orders.api.checkout_views.get_product",
        lambda _product_id: {
            "id": "p-1",
            "title": "Product 1",
            "price": "1000.00",
            "discount_percent": 10,
            "currency": "RUB",
            "image_url": "",
        },
    )

    response = api_client.post(
        "/api/checkout/confirm/",
        {
            "address": {
                "city": "Ekaterinburg",
                "postal_code": "620000",
                "street": "Lenina",
                "house": "1",
            },
            "shipping_provider": "demo",
            "shipping_type": "pickup",
            "pickup_point_id": "DEMO-1",
            "comment": "Call before delivery",
        },
        format="json",
    )

    assert response.status_code == 201
    payload = response.json()
    assert payload["status"] == "pending_payment"
    assert payload["total"] == 2100.0
    assert payload["order_secret"]

    order = Order.objects.get(id=payload["order_number"])
    assert order.status == OrderStatus.PENDING_PAYMENT
    assert order.shipping_provider == "demo"
    assert order.shipping_type == "pickup"
    assert order.pickup_point_id == "DEMO-1"
    assert order.shipping_price == Decimal("300.00")
    assert order.total == Decimal("2100.00")
    assert order.items.count() == 1
    order_item = order.items.get()
    assert order_item.product_title_snapshot == "Product 1"
    assert order_item.unit_price == Decimal("900.00")
    assert order_item.line_total == Decimal("1800.00")

    cart.refresh_from_db()
    assert cart.status == CartStatus.CHECKED_OUT


@pytest.mark.django_db
def test_checkout_preview_returns_400_when_shipping_provider_disabled(api_client, monkeypatch):
    _prepare_guest_cart(api_client)

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

    response = api_client.post(
        "/api/checkout/preview/",
        {
            "address": {
                "city": "Ekaterinburg",
                "postal_code": "620000",
                "street": "Lenina",
                "house": "1",
            },
            "shipping_provider": "demo",
            "shipping_type": "courier",
        },
        format="json",
    )

    assert response.status_code == 400
    assert response.json()["detail"] == ["Shipping provider is disabled."]


@pytest.mark.django_db
def test_shipping_pickup_points_returns_demo_points(api_client):
    response = api_client.get("/api/shipping/demo/pickup-points/?city=Moscow")

    assert response.status_code == 200
    payload = response.json()
    assert len(payload) == 3
    assert all(str(point.get("id", "")).startswith("DEMO-MSK-") for point in payload)
    assert all("Москва" in str(point.get("address", "")) for point in payload)
