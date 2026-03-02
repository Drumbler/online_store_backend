"""Модели настроек внешнего вида витрины и баннеров."""

from django.core.validators import MaxValueValidator
from django.core.validators import MinValueValidator
from django.db import models

from .validators import validate_logo_file


class ThemeMode(models.TextChoices):
    """Поддерживаемые режимы темы витрины."""

    LIGHT = "light", "Light"
    DARK = "dark", "Dark"


class PresetType(models.TextChoices):
    """Типы пресетов оформления, доступные в админке."""

    CATALOG_CARD = "catalog_card", "Catalog card"
    PRODUCT_PAGE = "product_page", "Product page"
    PRODUCT_CARD = "product_card", "Product card"


class LayoutMode(models.TextChoices):
    """Режимы компоновки элементов на странице товара."""

    MEDIA_LEFT = "media_left", "Media left"
    MEDIA_TOP = "media_top", "Media top"
    COMPACT = "compact", "Compact"


class PhotoMode(models.TextChoices):
    """Варианты отображения дополнительных изображений товара."""

    THUMBNAILS_RIGHT = "thumbnails_right", "Thumbnails right"
    THUMBNAILS_BOTTOM = "thumbnails_bottom", "Thumbnails bottom"
    HOVER_CAROUSEL = "hover_carousel", "Hover carousel"


class BannerPlacement(models.TextChoices):
    """Поддерживаемые места размещения баннеров."""

    BELOW_HEADER = "below_header", "Below header"
    IN_GRID = "in_grid", "In grid"


class AppearancePreset(models.Model):
    """Переиспользуемый пресет визуальных настроек интерфейса."""

    is_published = models.BooleanField(default=False, db_index=True)
    preset_type = models.CharField(max_length=32, choices=PresetType.choices)
    name = models.CharField(max_length=120)
    config = models.JSONField(default=dict)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["preset_type", "name", "id"]
        indexes = [
            models.Index(fields=["is_published", "preset_type"], name="app_preset_scope_type_idx"),
        ]

    def __str__(self) -> str:
        scope = "published" if self.is_published else "draft"
        return f"{self.name} ({self.preset_type}, {scope})"


class ShopAppearanceSettings(models.Model):
    """Глобальные настройки темы, сетки и активных пресетов магазина."""

    is_published = models.BooleanField(unique=True)
    theme_mode = models.CharField(max_length=16, choices=ThemeMode.choices, default=ThemeMode.LIGHT)
    primary_color = models.CharField(max_length=7, default="#ff6b00")
    grid_columns = models.PositiveSmallIntegerField(
        default=4,
        validators=[MinValueValidator(2), MaxValueValidator(6)],
    )
    card_height = models.PositiveIntegerField(
        default=320,
        validators=[MinValueValidator(240), MaxValueValidator(520)],
    )
    spacing_level = models.PositiveSmallIntegerField(
        default=2,
        validators=[MinValueValidator(0), MaxValueValidator(5)],
    )
    logo = models.ImageField(
        upload_to="appearance/logos/",
        null=True,
        blank=True,
        validators=[validate_logo_file],
    )
    active_catalog_preset = models.ForeignKey(
        "appearance.AppearancePreset",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    active_product_page_preset = models.ForeignKey(
        "appearance.AppearancePreset",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    active_product_card_preset = models.ForeignKey(
        "appearance.AppearancePreset",
        on_delete=models.SET_NULL,
        related_name="+",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["is_published"]

    def __str__(self) -> str:
        return "Published appearance" if self.is_published else "Draft appearance"


class AppearanceBanner(models.Model):
    """Модель рекламного баннера для витрины."""

    is_published = models.BooleanField(default=False, db_index=True)
    image_url = models.URLField(max_length=1000)
    link_url = models.URLField(max_length=1000)
    placement = models.CharField(max_length=32, choices=BannerPlacement.choices)
    after_row = models.PositiveIntegerField(null=True, blank=True)
    is_enabled = models.BooleanField(default=True)
    sort_order = models.IntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["sort_order", "id"]
        constraints = [
            models.CheckConstraint(
                check=(
                    (models.Q(placement=BannerPlacement.BELOW_HEADER) & models.Q(after_row__isnull=True))
                    | (models.Q(placement=BannerPlacement.IN_GRID) & models.Q(after_row__gte=1))
                ),
                name="appearance_banner_placement_rule",
            ),
        ]
        indexes = [
            models.Index(fields=["is_published", "is_enabled"], name="app_banner_scope_enabled_idx"),
        ]

    def __str__(self) -> str:
        scope = "published" if self.is_published else "draft"
        return f"Banner {self.id} ({self.placement}, {scope})"
