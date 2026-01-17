import pytest
from django.core.cache import cache
from rest_framework.test import APIClient


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture(autouse=True)
def clear_cache():
    cache.clear()


@pytest.mark.django_db
def test_products_list_returns_normalized_payload(api_client, monkeypatch):
    def fake_list_products(*, page, page_size, params=None):
        return (
            [
                {
                    "id": "doc-123",
                    "slug": "ceramic-mug",
                    "title": "Ceramic Mug",
                    "description": "Glazed ceramic mug.",
                    "price": "590.00",
                    "currency": "RUB",
                    "image_url": None,
                    "category": {
                        "id": "cat-1",
                        "slug": "kitchen",
                        "title": "Kitchen",
                    },
                }
            ],
            {"page": page, "page_size": page_size, "total": 1},
        )

    monkeypatch.setattr(
        "online_store_backend.products.api.views.list_products",
        fake_list_products,
    )

    response = api_client.get("/api/products/?page=1&page_size=20")

    assert response.status_code == 200
    payload = response.json()
    assert "results" in payload
    assert "pagination" in payload
    assert payload["results"][0]["id"] == "doc-123"


@pytest.mark.django_db
def test_products_detail_returns_normalized_payload(api_client, monkeypatch):
    def fake_get_product(document_id):
        return {
            "id": document_id,
            "slug": "ceramic-mug",
            "title": "Ceramic Mug",
            "description": None,
            "price": "590.00",
            "currency": "RUB",
            "image_url": None,
            "category": None,
        }

    monkeypatch.setattr(
        "online_store_backend.products.api.views.get_product",
        fake_get_product,
    )

    response = api_client.get("/api/products/doc-123/")

    assert response.status_code == 200
    payload = response.json()
    assert payload["id"] == "doc-123"
