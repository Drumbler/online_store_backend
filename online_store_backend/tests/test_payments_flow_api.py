import pytest
from django.utils import timezone
from rest_framework.test import APIClient

from online_store_backend.integrations.models import IntegrationConfig
from online_store_backend.integrations.models import IntegrationKind
from online_store_backend.orders.models import Order
from online_store_backend.orders.models import OrderStatus
from online_store_backend.orders.models import Payment
from online_store_backend.orders.models import PaymentStatus


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_payment_methods_lists_enabled_configs(api_client):
    IntegrationConfig.objects.create(
        kind=IntegrationKind.PAYMENT,
        provider_id="demo",
        enabled=True,
        is_sandbox=True,
        display_name="Demo checkout",
    )

    response = api_client.get("/api/checkout/payment-methods/")

    assert response.status_code == 200
    payload = response.json()["results"]
    assert len(payload) == 1
    assert payload[0]["provider_id"] == "demo"
    assert payload[0]["title"] == "Demo checkout"


@pytest.mark.django_db
def test_create_payment_idempotent_returns_existing_pending_payment(api_client, settings):
    settings.FRONTEND_URL = "http://localhost:5173"
    IntegrationConfig.objects.create(
        kind=IntegrationKind.PAYMENT,
        provider_id="demo",
        enabled=True,
        is_sandbox=True,
    )
    order = Order.objects.create(status=OrderStatus.PENDING_PAYMENT, total="100.00")

    payload = {
        "order_number": str(order.id),
        "order_secret": order.order_secret,
        "provider_id": "demo",
    }

    first = api_client.post("/api/payments/", payload, format="json")
    assert first.status_code == 201
    first_json = first.json()
    assert first_json["payment_url"].startswith("http://localhost:5173/demo-pay?")
    assert "external_id=" in first_json["payment_url"]
    assert "order_number=" in first_json["payment_url"]

    second = api_client.post("/api/payments/", payload, format="json")
    assert second.status_code == 200
    second_json = second.json()
    assert second_json["payment_id"] == first_json["payment_id"]
    assert second_json["external_id"] == first_json["external_id"]
    assert Payment.objects.filter(order=order).count() == 1


@pytest.mark.django_db
def test_webhook_succeeded_marks_payment_and_order_paid_idempotently(api_client):
    order = Order.objects.create(status=OrderStatus.PENDING_PAYMENT, total="100.00")
    payment = Payment.objects.create(
        order=order,
        provider_id="demo",
        status=PaymentStatus.PENDING,
        amount="100.00",
        currency="RUB",
        external_id="ext-1",
        payment_url="http://localhost:5173/demo-pay?external_id=ext-1&order_number=1",
    )

    first = api_client.post(
        "/api/payments/webhook/demo/",
        {"external_id": "ext-1", "status": "succeeded"},
        format="json",
    )
    assert first.status_code == 200
    assert first.json() == {"ok": True}

    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == PaymentStatus.SUCCEEDED
    assert payment.completed_at is not None
    assert order.status == OrderStatus.PAID
    assert order.paid_at is not None

    second = api_client.post(
        "/api/payments/webhook/demo/",
        {"external_id": "ext-1", "status": "succeeded"},
        format="json",
    )
    assert second.status_code == 200
    assert second.json() == {"ok": True, "already_processed": True}


@pytest.mark.django_db
def test_webhook_failed_sets_payment_failed_and_order_payment_failed(api_client):
    order = Order.objects.create(status=OrderStatus.PENDING_PAYMENT, total="100.00")
    payment = Payment.objects.create(
        order=order,
        provider_id="demo",
        status=PaymentStatus.PENDING,
        amount="100.00",
        currency="RUB",
        external_id="ext-fail",
    )

    response = api_client.post(
        "/api/payments/webhook/demo/",
        {"external_id": "ext-fail", "status": "failed"},
        format="json",
    )
    assert response.status_code == 200
    assert response.json() == {"ok": True}

    payment.refresh_from_db()
    order.refresh_from_db()
    assert payment.status == PaymentStatus.FAILED
    assert payment.completed_at is None
    assert order.status == OrderStatus.PAYMENT_FAILED
    assert order.paid_at is None


@pytest.mark.django_db
def test_create_payment_returns_409_for_paid_order(api_client):
    IntegrationConfig.objects.create(
        kind=IntegrationKind.PAYMENT,
        provider_id="demo",
        enabled=True,
    )
    order = Order.objects.create(status=OrderStatus.PAID, total="55.00", paid_at=timezone.now())

    response = api_client.post(
        "/api/payments/",
        {
            "order_number": str(order.id),
            "order_secret": order.order_secret,
            "provider_id": "demo",
        },
        format="json",
    )

    assert response.status_code == 409


@pytest.mark.django_db
def test_create_payment_requires_secret_for_guest(api_client):
    IntegrationConfig.objects.create(
        kind=IntegrationKind.PAYMENT,
        provider_id="demo",
        enabled=True,
    )
    order = Order.objects.create(status=OrderStatus.PENDING_PAYMENT, total="55.00")

    response = api_client.post(
        "/api/payments/",
        {
            "order_number": str(order.id),
            "provider_id": "demo",
        },
        format="json",
    )

    assert response.status_code == 400
    assert "order_secret" in response.json()
