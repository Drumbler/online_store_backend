import pytest
from rest_framework.test import APIClient

from online_store_backend.orders.models import Order
from online_store_backend.orders.models import Review


@pytest.fixture
def api_client():
    return APIClient()


@pytest.mark.django_db
def test_reviews_summary_returns_aggregates_for_multiple_products(api_client):
    order = Order.objects.create()
    Review.objects.create(product_id="p-1", order=order, rating=5, author_display_name="Alice")
    Review.objects.create(product_id="p-1", order=order, rating=4, author_display_name="Bob")
    Review.objects.create(product_id="p-2", order=order, rating=3, author_display_name="Carol")

    response = api_client.get("/api/reviews/summary/?product_ids=p-1,p-2,p-3")

    assert response.status_code == 200
    payload = response.json()["results"]
    assert payload["p-1"] == {"avg_rating": 4.5, "reviews_count": 2}
    assert payload["p-2"] == {"avg_rating": 3.0, "reviews_count": 1}
    assert payload["p-3"] == {"avg_rating": None, "reviews_count": 0}


@pytest.mark.django_db
def test_reviews_summary_requires_product_ids(api_client):
    response = api_client.get("/api/reviews/summary/")

    assert response.status_code == 400
    assert response.json()["detail"] == "product_ids query param is required."


@pytest.mark.django_db
def test_product_rating_summary_returns_single_product_summary(api_client):
    order = Order.objects.create()
    Review.objects.create(product_id="p-99", order=order, rating=5, author_display_name="Alice")
    Review.objects.create(product_id="p-99", order=order, rating=4, author_display_name="Bob")

    response = api_client.get("/api/products/p-99/rating-summary/")

    assert response.status_code == 200
    assert response.json() == {"avg_rating": 4.5, "reviews_count": 2}
