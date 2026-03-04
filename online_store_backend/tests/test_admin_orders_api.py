import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from online_store_backend.integrations.models import IntegrationConfig
from online_store_backend.integrations.models import IntegrationKind
from online_store_backend.orders.models import Order
from online_store_backend.orders.models import OrderDeliveryStatus
from online_store_backend.orders.models import OrderStatus


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="admin_orders",
        password="pass12345",
        is_staff=True,
        is_superuser=True,
    )


@pytest.mark.django_db
def test_admin_orders_list_requires_admin_permissions(api_client):
    response = api_client.get("/api/admin/orders/")
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_admin_orders_list_returns_required_columns(api_client, admin_user):
    user_model = get_user_model()
    customer = user_model.objects.create_user(
        username="buyer",
        password="pass12345",
        email="buyer@example.com",
    )
    Order.objects.create(
        user=customer,
        status=OrderStatus.PAID,
        total="1234.56",
        shipping_type="courier",
        shipping_provider="demo",
        delivery_status=OrderDeliveryStatus.READY_FOR_DISPATCH,
    )

    api_client.force_authenticate(user=admin_user)
    response = api_client.get("/api/admin/orders/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["pagination"]["total"] == 1
    row = payload["results"][0]
    assert set(["order_number", "user_display", "total", "delivery_type", "status"]).issubset(row.keys())
    assert row["user_display"] == "buyer"
    assert row["total"] == "1234.56"
    assert row["delivery_type"] == "courier"
    assert row["status"] == OrderDeliveryStatus.READY_FOR_DISPATCH


@pytest.mark.django_db
def test_admin_order_status_patch_updates_paid_order(api_client, admin_user):
    order = Order.objects.create(
        status=OrderStatus.PAID,
        total="100.00",
        shipping_type="courier",
        shipping_provider="demo",
        delivery_status=OrderDeliveryStatus.READY_FOR_DISPATCH,
    )
    api_client.force_authenticate(user=admin_user)

    response = api_client.patch(
        f"/api/admin/orders/{order.id}/status/",
        {
            "status": OrderDeliveryStatus.IN_TRANSIT,
            "tracking_number": "TRACK-1",
            "external_id": "ext-1",
            "status_note": "Courier accepted parcel.",
        },
        format="json",
    )

    assert response.status_code == 200
    order.refresh_from_db()
    assert order.delivery_status == OrderDeliveryStatus.IN_TRANSIT
    assert order.delivery_tracking_number == "TRACK-1"
    assert order.delivery_external_id == "ext-1"
    assert order.delivery_status_note == "Courier accepted parcel."


@pytest.mark.django_db
def test_user_orders_endpoint_reflects_admin_delivery_status_update(api_client, admin_user):
    user_model = get_user_model()
    customer = user_model.objects.create_user(
        username="buyer_status",
        password="pass12345",
        email="buyer_status@example.com",
    )
    order = Order.objects.create(
        user=customer,
        status=OrderStatus.PAID,
        total="100.00",
        shipping_type="courier",
        shipping_provider="demo",
        delivery_status=OrderDeliveryStatus.READY_FOR_DISPATCH,
    )

    api_client.force_authenticate(user=admin_user)
    patch_response = api_client.patch(
        f"/api/admin/orders/{order.id}/status/",
        {"status": OrderDeliveryStatus.IN_TRANSIT},
        format="json",
    )
    assert patch_response.status_code == 200

    api_client.force_authenticate(user=customer)
    user_orders = api_client.get("/api/orders/")
    assert user_orders.status_code == 200
    payload = user_orders.json()
    assert payload["count"] == 1
    assert payload["results"][0]["status"] == OrderDeliveryStatus.IN_TRANSIT
    assert payload["results"][0]["payment_status"] == OrderStatus.PAID


@pytest.mark.django_db
def test_admin_order_status_patch_rejects_unpaid_delivery_transition(api_client, admin_user):
    order = Order.objects.create(
        status=OrderStatus.PENDING_PAYMENT,
        total="100.00",
        shipping_type="courier",
        shipping_provider="demo",
        delivery_status=OrderDeliveryStatus.AWAITING_PAYMENT,
    )
    api_client.force_authenticate(user=admin_user)

    response = api_client.patch(
        f"/api/admin/orders/{order.id}/status/",
        {
            "status": OrderDeliveryStatus.IN_TRANSIT,
        },
        format="json",
    )

    assert response.status_code == 400
    order.refresh_from_db()
    assert order.delivery_status == OrderDeliveryStatus.AWAITING_PAYMENT


@pytest.mark.django_db
def test_shipping_webhook_updates_order_status_with_valid_secret(api_client):
    IntegrationConfig.objects.create(
        kind=IntegrationKind.SHIPPING,
        provider_id="demo",
        enabled=True,
        credentials={"webhook_secret": "whsec-demo"},
    )
    order = Order.objects.create(
        status=OrderStatus.PAID,
        total="100.00",
        shipping_type="courier",
        shipping_provider="demo",
        delivery_status=OrderDeliveryStatus.READY_FOR_DISPATCH,
    )

    response = api_client.post(
        "/api/shipping/webhook/demo/",
        {
            "order_number": order.id,
            "status": OrderDeliveryStatus.DELIVERED,
            "tracking_number": "TRACK-42",
            "external_id": "ext-42",
            "status_note": "Delivered to recipient.",
        },
        format="json",
        HTTP_X_WEBHOOK_SECRET="whsec-demo",
    )

    assert response.status_code == 200
    assert response.json()["ok"] is True
    assert response.json()["status"] == OrderDeliveryStatus.DELIVERED
    order.refresh_from_db()
    assert order.delivery_status == OrderDeliveryStatus.DELIVERED
    assert order.delivery_tracking_number == "TRACK-42"
    assert order.delivery_external_id == "ext-42"
    assert order.delivery_status_note == "Delivered to recipient."


@pytest.mark.django_db
def test_shipping_webhook_rejects_invalid_secret(api_client):
    IntegrationConfig.objects.create(
        kind=IntegrationKind.SHIPPING,
        provider_id="demo",
        enabled=True,
        credentials={"webhook_secret": "whsec-demo"},
    )
    order = Order.objects.create(
        status=OrderStatus.PAID,
        total="100.00",
        shipping_provider="demo",
        delivery_status=OrderDeliveryStatus.READY_FOR_DISPATCH,
    )

    response = api_client.post(
        "/api/shipping/webhook/demo/",
        {"order_number": order.id, "status": OrderDeliveryStatus.IN_TRANSIT},
        format="json",
        HTTP_X_WEBHOOK_SECRET="wrong-secret",
    )

    assert response.status_code == 403
