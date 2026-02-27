from django.contrib import admin

from .models import AppearanceBanner
from .models import AppearancePreset
from .models import ShopAppearanceSettings


@admin.register(ShopAppearanceSettings)
class ShopAppearanceSettingsAdmin(admin.ModelAdmin):
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
    list_display = ("id", "name", "preset_type", "is_published", "updated_at")
    list_filter = ("is_published", "preset_type")
    search_fields = ("name",)


@admin.register(AppearanceBanner)
class AppearanceBannerAdmin(admin.ModelAdmin):
    list_display = ("id", "placement", "after_row", "is_enabled", "is_published", "sort_order", "updated_at")
    list_filter = ("is_published", "is_enabled", "placement")
    search_fields = ("image_url", "link_url")
