"""Сервисный слой управления оформлением витрины магазина."""

from __future__ import annotations

from copy import deepcopy

from django.db import transaction

from .models import AppearanceBanner
from .models import AppearancePreset
from .models import LayoutMode
from .models import PhotoMode
from .models import PresetType
from .models import ShopAppearanceSettings
from .models import ThemeMode

BLOCK_TYPES = (
    "title",
    "price",
    "rating",
    "reviews_count",
    "buy_button",
    "short_description",
)


def _default_blocks(visible_overrides: dict[str, bool] | None = None):
    """Сформировать дефолтный порядок и видимость блоков карточек."""
    overrides = visible_overrides or {}
    result = []
    for index, block_type in enumerate(BLOCK_TYPES):
        result.append(
            {
                "type": block_type,
                "visible": bool(overrides.get(block_type, True)),
                "order": index,
            }
        )
    return result


DEFAULT_PRESET_CONFIGS = {
    PresetType.CATALOG_CARD: {
        "layout_mode": LayoutMode.MEDIA_TOP,
        "photo_mode": PhotoMode.HOVER_CAROUSEL,
        "blocks": _default_blocks(
            {
                "short_description": False,
            }
        ),
    },
    PresetType.PRODUCT_PAGE: {
        "layout_mode": LayoutMode.MEDIA_LEFT,
        "photo_mode": PhotoMode.THUMBNAILS_BOTTOM,
        "blocks": _default_blocks(),
    },
    PresetType.PRODUCT_CARD: {
        "layout_mode": LayoutMode.COMPACT,
        "photo_mode": PhotoMode.THUMBNAILS_BOTTOM,
        "blocks": _default_blocks(
            {
                "short_description": False,
            }
        ),
    },
}


def default_preset_config(preset_type: str):
    """Вернуть копию стандартной конфигурации пресета по его типу."""
    config = DEFAULT_PRESET_CONFIGS.get(preset_type) or DEFAULT_PRESET_CONFIGS[PresetType.CATALOG_CARD]
    return deepcopy(config)


def normalize_preset_config(raw_config, preset_type: str):
    """Нормализовать конфигурацию пресета к допустимым значениям и порядку блоков."""
    config = raw_config if isinstance(raw_config, dict) else {}

    layout_mode = config.get("layout_mode")
    if layout_mode not in LayoutMode.values:
        layout_mode = default_preset_config(preset_type)["layout_mode"]

    photo_mode = config.get("photo_mode")
    if photo_mode not in PhotoMode.values:
        photo_mode = default_preset_config(preset_type)["photo_mode"]

    defaults = {item["type"]: item for item in default_preset_config(preset_type)["blocks"]}
    blocks_by_type = {
        block_type: {
            "type": block_type,
            "visible": bool(defaults[block_type]["visible"]),
            "order": int(defaults[block_type]["order"]),
        }
        for block_type in BLOCK_TYPES
    }

    raw_blocks = config.get("blocks") if isinstance(config.get("blocks"), list) else []
    for item in raw_blocks:
        if not isinstance(item, dict):
            continue
        block_type = item.get("type")
        if block_type not in BLOCK_TYPES:
            continue
        try:
            order = int(item.get("order", blocks_by_type[block_type]["order"]))
        except (TypeError, ValueError):
            order = blocks_by_type[block_type]["order"]
        blocks_by_type[block_type] = {
            "type": block_type,
            "visible": bool(item.get("visible", blocks_by_type[block_type]["visible"])),
            "order": order,
        }

    sorted_blocks = sorted(blocks_by_type.values(), key=lambda block: (int(block["order"]), block["type"]))
    normalized_blocks = []
    for index, block in enumerate(sorted_blocks):
        normalized_blocks.append(
            {
                "type": block["type"],
                "visible": bool(block["visible"]),
                "order": index,
            }
        )

    return {
        "layout_mode": layout_mode,
        "photo_mode": photo_mode,
        "blocks": normalized_blocks,
    }


def _settings_defaults():
    """Дефолтные значения настроек оформления."""
    return {
        "theme_mode": ThemeMode.LIGHT,
        "primary_color": "#ff6b00",
        "grid_columns": 4,
        "card_height": 320,
        "spacing_level": 2,
    }


def _create_stock_presets(scope: bool):
    """Создать набор штатных пресетов для draft/published-области."""
    presets = {}
    names = {
        PresetType.CATALOG_CARD: "Catalog card (stock)",
        PresetType.PRODUCT_PAGE: "Product page (stock)",
        PresetType.PRODUCT_CARD: "Product card (stock)",
    }
    for preset_type in PresetType.values:
        preset = AppearancePreset.objects.create(
            is_published=scope,
            preset_type=preset_type,
            name=names[preset_type],
            config=default_preset_config(preset_type),
        )
        presets[preset_type] = preset
    return presets


def _ensure_scope_defaults(settings_obj: ShopAppearanceSettings):
    """Проверить и восстановить обязательные пресеты/ссылки внутри одной области."""
    scope = bool(settings_obj.is_published)
    presets_queryset = AppearancePreset.objects.filter(is_published=scope)

    if not presets_queryset.exists():
        created = _create_stock_presets(scope)
        settings_obj.active_catalog_preset = created[PresetType.CATALOG_CARD]
        settings_obj.active_product_page_preset = created[PresetType.PRODUCT_PAGE]
        settings_obj.active_product_card_preset = created[PresetType.PRODUCT_CARD]
        settings_obj.save()
        return

    for preset in presets_queryset:
        normalized = normalize_preset_config(preset.config, preset.preset_type)
        if preset.config != normalized:
            preset.config = normalized
            preset.save(update_fields=["config", "updated_at"])

    by_type = {}
    for preset_type in PresetType.values:
        preset = (
            AppearancePreset.objects.filter(is_published=scope, preset_type=preset_type)
            .order_by("id")
            .first()
        )
        if preset is None:
            preset = AppearancePreset.objects.create(
                is_published=scope,
                preset_type=preset_type,
                name=f"{preset_type.replace('_', ' ').title()} (stock)",
                config=default_preset_config(preset_type),
            )
        by_type[preset_type] = preset

    changed = False
    if (
        settings_obj.active_catalog_preset_id is None
        or settings_obj.active_catalog_preset_id
        not in AppearancePreset.objects.filter(is_published=scope, preset_type=PresetType.CATALOG_CARD).values_list("id", flat=True)
    ):
        settings_obj.active_catalog_preset = by_type[PresetType.CATALOG_CARD]
        changed = True

    if (
        settings_obj.active_product_page_preset_id is None
        or settings_obj.active_product_page_preset_id
        not in AppearancePreset.objects.filter(is_published=scope, preset_type=PresetType.PRODUCT_PAGE).values_list("id", flat=True)
    ):
        settings_obj.active_product_page_preset = by_type[PresetType.PRODUCT_PAGE]
        changed = True

    if (
        settings_obj.active_product_card_preset_id is None
        or settings_obj.active_product_card_preset_id
        not in AppearancePreset.objects.filter(is_published=scope, preset_type=PresetType.PRODUCT_CARD).values_list("id", flat=True)
    ):
        settings_obj.active_product_card_preset = by_type[PresetType.PRODUCT_CARD]
        changed = True

    if changed:
        settings_obj.save()


@transaction.atomic
def ensure_shop_appearance_initialized():
    """Инициализировать draft/live-настройки и базовые пресеты при первом запуске."""
    draft, _ = ShopAppearanceSettings.objects.get_or_create(is_published=False, defaults=_settings_defaults())
    published, _ = ShopAppearanceSettings.objects.get_or_create(is_published=True, defaults=_settings_defaults())

    _ensure_scope_defaults(draft)
    _ensure_scope_defaults(published)
    return draft, published


def get_scope_settings(is_published: bool):
    """Получить настройки нужной области (`draft` или `published`)."""
    ensure_shop_appearance_initialized()
    return ShopAppearanceSettings.objects.select_related(
        "active_catalog_preset",
        "active_product_page_preset",
        "active_product_card_preset",
    ).get(is_published=is_published)


def serialize_preset(preset: AppearancePreset | None):
    """Сериализовать пресет в API-формат."""
    if preset is None:
        return None
    return {
        "id": preset.id,
        "preset_type": preset.preset_type,
        "name": preset.name,
        "config": normalize_preset_config(preset.config, preset.preset_type),
    }


def serialize_banner(banner: AppearanceBanner):
    """Сериализовать баннер в API-формат."""
    return {
        "id": banner.id,
        "image_url": banner.image_url,
        "link_url": banner.link_url,
        "placement": banner.placement,
        "after_row": banner.after_row,
        "is_enabled": banner.is_enabled,
        "sort_order": banner.sort_order,
    }


def _build_logo_url(settings_obj: ShopAppearanceSettings, request=None):
    """Вернуть URL логотипа в виде, который отдает storage backend."""
    if not settings_obj.logo:
        return None
    try:
        return settings_obj.logo.url
    except ValueError:
        return None


def serialize_settings(settings_obj: ShopAppearanceSettings, request=None):
    """Сериализовать настройки оформления для админ-редактора."""
    logo_url = _build_logo_url(settings_obj, request=request)
    return {
        "id": settings_obj.id,
        "theme_mode": settings_obj.theme_mode,
        "primary_color": settings_obj.primary_color,
        "logo_url": logo_url,
        "grid_columns": settings_obj.grid_columns,
        "card_height": settings_obj.card_height,
        "spacing_level": settings_obj.spacing_level,
        "active_catalog_preset_id": settings_obj.active_catalog_preset_id,
        "active_product_page_preset_id": settings_obj.active_product_page_preset_id,
        "active_product_card_preset_id": settings_obj.active_product_card_preset_id,
    }


def public_appearance_payload(request=None):
    """Собрать опубликованные настройки оформления для публичной витрины."""
    settings_obj = get_scope_settings(is_published=True)
    logo_url = _build_logo_url(settings_obj, request=request)
    banners = (
        AppearanceBanner.objects.filter(is_published=True, is_enabled=True)
        .order_by("placement", "after_row", "sort_order", "id")
    )
    return {
        "theme_mode": settings_obj.theme_mode,
        "primary_color": settings_obj.primary_color,
        "logo_url": logo_url,
        "grid_columns": settings_obj.grid_columns,
        "card_height": settings_obj.card_height,
        "spacing_level": settings_obj.spacing_level,
        "presets": {
            "catalog_card": serialize_preset(settings_obj.active_catalog_preset),
            "product_page": serialize_preset(settings_obj.active_product_page_preset),
            "product_card": serialize_preset(settings_obj.active_product_card_preset),
        },
        "banners": [serialize_banner(item) for item in banners],
    }


def _copy_scope(source_is_published: bool, target_is_published: bool):
    """Скопировать настройки/пресеты/баннеры между draft и published областями."""
    source_settings = get_scope_settings(source_is_published)
    target_settings = get_scope_settings(target_is_published)

    source_presets = list(
        AppearancePreset.objects.filter(is_published=source_is_published).order_by("id")
    )
    source_banners = list(
        AppearanceBanner.objects.filter(is_published=source_is_published).order_by("id")
    )

    target_settings.active_catalog_preset = None
    target_settings.active_product_page_preset = None
    target_settings.active_product_card_preset = None
    target_settings.save()

    AppearancePreset.objects.filter(is_published=target_is_published).delete()
    AppearanceBanner.objects.filter(is_published=target_is_published).delete()

    cloned_presets = AppearancePreset.objects.bulk_create(
        [
            AppearancePreset(
                is_published=target_is_published,
                preset_type=item.preset_type,
                name=item.name,
                config=normalize_preset_config(item.config, item.preset_type),
            )
            for item in source_presets
        ]
    )
    preset_mapping = {
        source.id: created
        for source, created in zip(source_presets, cloned_presets, strict=False)
    }

    target_settings.theme_mode = source_settings.theme_mode
    target_settings.primary_color = source_settings.primary_color
    target_settings.logo = source_settings.logo
    target_settings.grid_columns = source_settings.grid_columns
    target_settings.card_height = source_settings.card_height
    target_settings.spacing_level = source_settings.spacing_level
    target_settings.active_catalog_preset = preset_mapping.get(source_settings.active_catalog_preset_id)
    target_settings.active_product_page_preset = preset_mapping.get(source_settings.active_product_page_preset_id)
    target_settings.active_product_card_preset = preset_mapping.get(source_settings.active_product_card_preset_id)
    target_settings.save()

    AppearanceBanner.objects.bulk_create(
        [
            AppearanceBanner(
                is_published=target_is_published,
                image_url=item.image_url,
                link_url=item.link_url,
                placement=item.placement,
                after_row=item.after_row,
                is_enabled=item.is_enabled,
                sort_order=item.sort_order,
            )
            for item in source_banners
        ]
    )

    return get_scope_settings(target_is_published)


@transaction.atomic
def publish_draft_to_live():
    """Опубликовать текущий draft в live-область."""
    ensure_shop_appearance_initialized()
    return _copy_scope(source_is_published=False, target_is_published=True)


@transaction.atomic
def reset_draft_from_live():
    """Сбросить draft, скопировав туда актуальную live-конфигурацию."""
    ensure_shop_appearance_initialized()
    return _copy_scope(source_is_published=True, target_is_published=False)
