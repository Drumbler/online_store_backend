"""Админ-конфигурация для сущностей внешнего вида витрины."""

from django.contrib import admin

from .models import AppearanceBanner
from .models import AppearancePreset
from .models import ShopAppearanceSettings


@admin.register(ShopAppearanceSettings)
class ShopAppearanceSettingsAdmin(admin.ModelAdmin):
    """Настройки отображения магазина в черновом/публичном скоупе."""

    list_display = (
        "id",
        "is_published",
        "theme_mode",
        "primary_color",
        "grid_columns",
        "card_height",
        "spacing_level",
        "updated_at",
    )
    list_filter = ("is_published", "theme_mode")


@admin.register(AppearancePreset)
class AppearancePresetAdmin(admin.ModelAdmin):
    """Админка для управления пресетами карточек и страниц."""

    list_display = ("id", "name", "preset_type", "is_published", "updated_at")
    list_filter = ("is_published", "preset_type")
    search_fields = ("name",)


@admin.register(AppearanceBanner)
class AppearanceBannerAdmin(admin.ModelAdmin):
    """Админка для рекламных баннеров витрины."""

    list_display = ("id", "placement", "after_row", "is_enabled", "is_published", "sort_order", "updated_at")
    list_filter = ("is_published", "is_enabled", "placement")
    search_fields = ("image_url", "link_url")
