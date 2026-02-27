import pytest
from django.contrib.auth import get_user_model
from rest_framework.test import APIClient

from online_store_backend.integrations.models import IntegrationConfig


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="admin-int",
        password="pass12345",
        is_staff=True,
        is_superuser=True,
    )


@pytest.mark.django_db
def test_admin_integrations_requires_admin(api_client):
    response = api_client.get("/api/admin/integrations/providers/")
    assert response.status_code in {401, 403}


@pytest.mark.django_db
def test_admin_integrations_upsert_masks_secrets_and_test(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)

    providers = api_client.get("/api/admin/integrations/providers/")
    assert providers.status_code == 200
    assert providers.json()["payment"][0]["id"] == "demo"

    saved = api_client.put(
        "/api/admin/integrations/configs/payment/demo/",
        {
            "enabled": True,
            "is_sandbox": True,
            "display_name": "Demo Pay",
            "credentials": {"api_key": "secret123", "merchant_id": "m-1"},
            "settings": {},
        },
        format="json",
    )
    assert saved.status_code == 200
    assert saved.json()["credentials"]["api_key"] == "******"

    model = IntegrationConfig.objects.get(kind="payment", provider_id="demo")
    assert model.credentials["api_key"] == "secret123"

    keep_secret = api_client.put(
        "/api/admin/integrations/configs/payment/demo/",
        {
            "enabled": True,
            "credentials": {"api_key": "******"},
            "settings": {},
        },
        format="json",
    )
    assert keep_secret.status_code == 200
    model.refresh_from_db()
    assert model.credentials["api_key"] == "secret123"

    tested = api_client.post("/api/admin/integrations/configs/payment/demo/test/", {}, format="json")
    assert tested.status_code == 200
    assert tested.json()["ok"] is True


@pytest.mark.django_db
def test_unknown_provider_returns_404(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)
    response = api_client.get("/api/admin/integrations/configs/payment/unknown/")
    assert response.status_code == 404
