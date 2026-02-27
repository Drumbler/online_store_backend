from rest_framework import serializers

from ..models import AppearanceBanner
from ..models import AppearancePreset
from ..models import BannerPlacement
from ..models import PresetType
from ..models import ThemeMode
from ..services import default_preset_config
from ..services import normalize_preset_config
from ..validators import validate_logo_file


class DraftAppearanceSettingsSerializer(serializers.Serializer):
    theme_mode = serializers.ChoiceField(choices=ThemeMode.values, required=False)
    primary_color = serializers.RegexField(regex=r"^#[0-9A-Fa-f]{6}$", required=False)
    logo = serializers.ImageField(required=False, allow_null=True, validators=[validate_logo_file])
    clear_logo = serializers.BooleanField(required=False, default=False)
    grid_columns = serializers.ChoiceField(choices=[2, 3, 4, 5, 6], required=False)
    card_height = serializers.IntegerField(min_value=240, max_value=520, required=False)
    spacing_level = serializers.IntegerField(min_value=0, max_value=5, required=False)
    active_catalog_preset_id = serializers.IntegerField(required=False)
    active_product_page_preset_id = serializers.IntegerField(required=False)
    active_product_card_preset_id = serializers.IntegerField(required=False)

    def _validate_active_preset(self, preset_id, preset_type, field_name):
        exists = AppearancePreset.objects.filter(
            id=preset_id,
            is_published=False,
            preset_type=preset_type,
        ).exists()
        if not exists:
            raise serializers.ValidationError(
                {field_name: "Active preset must reference an existing draft preset of matching type."}
            )
        return preset_id

    def validate(self, attrs):
        if attrs.get("clear_logo") and attrs.get("logo"):
            raise serializers.ValidationError({"logo": "Upload logo or clear it, but not both at once."})

        if "active_catalog_preset_id" in attrs:
            self._validate_active_preset(
                attrs["active_catalog_preset_id"],
                PresetType.CATALOG_CARD,
                "active_catalog_preset_id",
            )

        if "active_product_page_preset_id" in attrs:
            self._validate_active_preset(
                attrs["active_product_page_preset_id"],
                PresetType.PRODUCT_PAGE,
                "active_product_page_preset_id",
            )

        if "active_product_card_preset_id" in attrs:
            self._validate_active_preset(
                attrs["active_product_card_preset_id"],
                PresetType.PRODUCT_CARD,
                "active_product_card_preset_id",
            )

        return attrs


class AppearancePresetSerializer(serializers.ModelSerializer):
    preset_type = serializers.ChoiceField(choices=PresetType.values)

    class Meta:
        model = AppearancePreset
        fields = (
            "id",
            "preset_type",
            "name",
            "config",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        instance = getattr(self, "instance", None)
        preset_type = attrs.get("preset_type") or (instance.preset_type if instance else None)
        if not preset_type:
            raise serializers.ValidationError({"preset_type": "This field is required."})

        if instance and "preset_type" in attrs and attrs["preset_type"] != instance.preset_type:
            raise serializers.ValidationError({"preset_type": "Changing preset_type is not allowed."})

        raw_config = attrs.get("config")
        if raw_config is None:
            if instance:
                raw_config = instance.config
            else:
                raw_config = default_preset_config(preset_type)
        attrs["config"] = normalize_preset_config(raw_config, preset_type)
        return attrs


class AppearanceBannerSerializer(serializers.ModelSerializer):
    placement = serializers.ChoiceField(choices=BannerPlacement.values)

    class Meta:
        model = AppearanceBanner
        fields = (
            "id",
            "image_url",
            "link_url",
            "placement",
            "after_row",
            "is_enabled",
            "sort_order",
            "created_at",
            "updated_at",
        )
        read_only_fields = ("id", "created_at", "updated_at")

    def validate(self, attrs):
        placement = attrs.get("placement")
        after_row = attrs.get("after_row")

        instance = getattr(self, "instance", None)
        if instance:
            if placement is None:
                placement = instance.placement
            if "after_row" not in attrs:
                after_row = instance.after_row

        if placement == BannerPlacement.IN_GRID:
            if after_row in (None, ""):
                raise serializers.ValidationError({"after_row": "after_row is required for in_grid placement."})
            if int(after_row) < 1:
                raise serializers.ValidationError({"after_row": "after_row must be greater than or equal to 1."})

        if placement == BannerPlacement.BELOW_HEADER:
            attrs["after_row"] = None

        return attrs
