import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from online_store_backend.orders.models import Order
from online_store_backend.orders.models import Review


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="admin",
        password="pass12345",
        is_staff=True,
        is_superuser=True,
    )


@pytest.mark.django_db
def test_public_product_reviews_returns_only_published(api_client):
    order = Order.objects.create()
    Review.objects.create(
        product_id="p-1",
        order=order,
        rating=5,
        author_display_name="Alice",
        is_published=True,
    )
    Review.objects.create(
        product_id="p-1",
        order=order,
        rating=2,
        author_display_name="Bob",
        is_published=False,
    )

    response = api_client.get("/api/products/p-1/reviews/")

    assert response.status_code == 200
    payload = response.json()["results"]
    assert len(payload) == 1
    assert payload[0]["author_display_name"] == "Alice"


@pytest.mark.django_db
def test_admin_reviews_list_and_patch_and_bulk(api_client, admin_user, monkeypatch):
    monkeypatch.setattr(
        "online_store_backend.orders.api.admin_views.get_product",
        lambda product_id: {
            "id": product_id,
            "title": f"Product {product_id}",
            "image_url": f"https://img/{product_id}.jpg",
        },
    )

    order = Order.objects.create()
    review_1 = Review.objects.create(
        product_id="p-1",
        order=order,
        rating=5,
        author_display_name="Alice",
        comment="Great",
    )
    review_2 = Review.objects.create(
        product_id="p-2",
        order=order,
        rating=1,
        author_display_name="Bob",
        comment="Bad",
        is_published=False,
    )

    api_client.force_authenticate(user=admin_user)

    list_response = api_client.get("/api/admin/reviews/?is_published=all&sort=created_desc")
    assert list_response.status_code == 200
    list_payload = list_response.json()["results"]
    assert len(list_payload) == 2
    assert list_payload[0]["product_title"] is not None
    assert "is_published" in list_payload[0]

    patch_response = api_client.patch(
        f"/api/admin/reviews/{review_1.id}/",
        {"is_published": False},
        format="json",
    )
    assert patch_response.status_code == 200
    assert patch_response.json()["is_published"] is False

    bulk_response = api_client.post(
        "/api/admin/reviews/bulk/",
        {"ids": [review_1.id, review_2.id], "is_published": True},
        format="json",
    )
    assert bulk_response.status_code == 200
    assert bulk_response.json()["updated"] >= 1
