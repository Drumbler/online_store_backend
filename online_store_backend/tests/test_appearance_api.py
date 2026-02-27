import io

import pytest
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from rest_framework.test import APIClient
from PIL import Image

from online_store_backend.appearance.models import AppearancePreset
from online_store_backend.appearance.models import PresetType
from online_store_backend.appearance.models import ShopAppearanceSettings


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def admin_user(db):
    user_model = get_user_model()
    return user_model.objects.create_user(
        username="admin_appearance",
        password="pass12345",
        is_staff=True,
        is_superuser=True,
    )


def build_logo_file(name: str, size: tuple[int, int]):
    buffer = io.BytesIO()
    image = Image.new("RGB", size=size, color=(237, 51, 59))
    image.save(buffer, format="PNG")
    buffer.seek(0)
    return SimpleUploadedFile(name=name, content=buffer.read(), content_type="image/png")


@pytest.mark.django_db
def test_public_appearance_isolated_from_draft_until_publish(api_client, admin_user):
    public_before = api_client.get("/api/shop/appearance/")
    assert public_before.status_code == 200
    initial_color = public_before.json()["primary_color"]

    api_client.force_authenticate(user=admin_user)

    draft_response = api_client.get("/api/admin/appearance/draft/")
    assert draft_response.status_code == 200
    draft_payload = draft_response.json()

    update_response = api_client.put(
        "/api/admin/appearance/draft/",
        {
            "theme_mode": "dark",
            "primary_color": "#123abc",
            "grid_columns": 6,
            "card_height": 500,
            "spacing_level": 5,
            "active_catalog_preset_id": draft_payload["active_catalog_preset_id"],
            "active_product_page_preset_id": draft_payload["active_product_page_preset_id"],
            "active_product_card_preset_id": draft_payload["active_product_card_preset_id"],
        },
        format="json",
    )
    assert update_response.status_code == 200

    banner_response = api_client.post(
        "/api/admin/appearance/banners/",
        {
            "image_url": "https://example.com/banner-draft.jpg",
            "link_url": "https://example.com/landing",
            "placement": "below_header",
            "is_enabled": True,
            "sort_order": 1,
        },
        format="json",
    )
    assert banner_response.status_code == 201

    public_still_old = api_client.get("/api/shop/appearance/")
    assert public_still_old.status_code == 200
    assert public_still_old.json()["primary_color"] == initial_color

    publish_response = api_client.post("/api/admin/appearance/publish/", {}, format="json")
    assert publish_response.status_code == 200
    assert publish_response.json() == {"ok": True}

    public_after = api_client.get("/api/shop/appearance/")
    assert public_after.status_code == 200
    payload = public_after.json()
    assert payload["theme_mode"] == "dark"
    assert payload["primary_color"] == "#123abc"
    assert payload["grid_columns"] == 6
    assert payload["card_height"] == 500
    assert payload["spacing_level"] == 5
    assert len(payload["banners"]) == 1


@pytest.mark.django_db
def test_reset_restores_draft_from_published(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)

    seed = api_client.put(
        "/api/admin/appearance/draft/",
        {
            "theme_mode": "dark",
            "primary_color": "#654321",
        },
        format="json",
    )
    assert seed.status_code == 200
    publish = api_client.post("/api/admin/appearance/publish/", {}, format="json")
    assert publish.status_code == 200

    mutate = api_client.put(
        "/api/admin/appearance/draft/",
        {
            "theme_mode": "light",
            "primary_color": "#00ff00",
        },
        format="json",
    )
    assert mutate.status_code == 200

    reset = api_client.post("/api/admin/appearance/reset/", {}, format="json")
    assert reset.status_code == 200
    assert reset.json()["ok"] is True

    draft = api_client.get("/api/admin/appearance/draft/")
    assert draft.status_code == 200
    assert draft.json()["theme_mode"] == "dark"
    assert draft.json()["primary_color"] == "#654321"


@pytest.mark.django_db
def test_cannot_delete_active_preset(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)

    draft = api_client.get("/api/admin/appearance/draft/")
    assert draft.status_code == 200
    active_catalog_id = draft.json()["active_catalog_preset_id"]

    delete_active = api_client.delete(f"/api/admin/appearance/presets/{active_catalog_id}/")
    assert delete_active.status_code == 400

    create_new = api_client.post(
        "/api/admin/appearance/presets/",
        {
            "preset_type": PresetType.CATALOG_CARD,
            "name": "Alt catalog",
            "config": {
                "layout_mode": "media_left",
                "photo_mode": "thumbnails_bottom",
                "blocks": [
                    {"type": "title", "visible": True, "order": 0},
                    {"type": "price", "visible": True, "order": 1},
                    {"type": "rating", "visible": True, "order": 2},
                    {"type": "reviews_count", "visible": True, "order": 3},
                    {"type": "buy_button", "visible": True, "order": 4},
                    {"type": "short_description", "visible": False, "order": 5},
                ],
            },
        },
        format="json",
    )
    assert create_new.status_code == 201
    new_preset_id = create_new.json()["id"]

    switch_active = api_client.put(
        "/api/admin/appearance/draft/",
        {"active_catalog_preset_id": new_preset_id},
        format="json",
    )
    assert switch_active.status_code == 200

    delete_old = api_client.delete(f"/api/admin/appearance/presets/{active_catalog_id}/")
    assert delete_old.status_code == 204

    assert not AppearancePreset.objects.filter(id=active_catalog_id, is_published=False).exists()


@pytest.mark.django_db
def test_initialization_creates_exactly_two_settings_rows(api_client):
    response = api_client.get("/api/shop/appearance/")
    assert response.status_code == 200

    rows = ShopAppearanceSettings.objects.all()
    assert rows.count() == 2
    assert rows.filter(is_published=True).count() == 1
    assert rows.filter(is_published=False).count() == 1


@pytest.mark.django_db
def test_logo_upload_is_returned_only_after_publish(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)

    upload = api_client.put(
        "/api/admin/appearance/draft/",
        {"logo": build_logo_file("logo.png", (240, 240))},
        format="multipart",
    )
    assert upload.status_code == 200
    draft_logo_url = upload.json()["logo_url"]
    assert draft_logo_url
    assert "appearance/logos/" in draft_logo_url

    public_before_publish = api_client.get("/api/shop/appearance/")
    assert public_before_publish.status_code == 200
    assert public_before_publish.json()["logo_url"] in (None, "")

    publish = api_client.post("/api/admin/appearance/publish/", {}, format="json")
    assert publish.status_code == 200

    public_after_publish = api_client.get("/api/shop/appearance/")
    assert public_after_publish.status_code == 200
    public_logo_url = public_after_publish.json()["logo_url"]
    assert public_logo_url
    assert "appearance/logos/" in public_logo_url


@pytest.mark.django_db
def test_logo_must_be_square(api_client, admin_user):
    api_client.force_authenticate(user=admin_user)

    upload = api_client.put(
        "/api/admin/appearance/draft/",
        {"logo": build_logo_file("logo.png", (320, 200))},
        format="multipart",
    )
    assert upload.status_code == 400
    assert "logo" in upload.json()
