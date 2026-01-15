from django.utils.text import slugify
from rest_framework import serializers


class CategoryAdminSerializer(serializers.Serializer):
    id = serializers.CharField()
    slug = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    title = serializers.CharField(allow_null=True, allow_blank=True, required=False)


class ProductAdminCategorySerializer(serializers.Serializer):
    id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    slug = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    title = serializers.CharField(allow_null=True, allow_blank=True, required=False)


class ProductAdminSerializer(serializers.Serializer):
    id = serializers.CharField()
    slug = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    title = serializers.CharField()
    description = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    price = serializers.CharField()
    currency = serializers.CharField()
    category = ProductAdminCategorySerializer(allow_null=True, required=False)


class CategoryUpsertSerializer(serializers.Serializer):
    title = serializers.CharField(required=True, allow_blank=False)
    slug = serializers.CharField(required=False, allow_blank=True, allow_null=True)

    def validate(self, attrs):
        slug_provided = "slug" in attrs
        title = attrs.get("title")
        slug = attrs.get("slug") if slug_provided else None
        if slug_provided:
            if not slug:
                if title is None:
                    raise serializers.ValidationError({"slug": "Slug cannot be blank."})
                slug = slugify(title or "")
                if not slug:
                    raise serializers.ValidationError({"slug": "Unable to generate slug."})
                attrs["slug"] = slug
        elif title is not None:
            slug = slugify(title or "")
            if not slug:
                raise serializers.ValidationError({"slug": "Unable to generate slug."})
            attrs["slug"] = slug
        return attrs


class ProductUpsertSerializer(serializers.Serializer):
    title = serializers.CharField(required=True, allow_blank=False)
    slug = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    price = serializers.DecimalField(max_digits=12, decimal_places=2, min_value=0)
    currency = serializers.CharField(required=True, allow_blank=False)
    category = serializers.CharField(required=False, allow_null=True, allow_blank=True)
    publish = serializers.BooleanField(required=False, default=True)

    def validate(self, attrs):
        slug_provided = "slug" in attrs
        title = attrs.get("title")
        slug = attrs.get("slug") if slug_provided else None
        if slug_provided:
            if not slug:
                if title is None:
                    raise serializers.ValidationError({"slug": "Slug cannot be blank."})
                slug = slugify(title or "")
                if not slug:
                    raise serializers.ValidationError({"slug": "Unable to generate slug."})
                attrs["slug"] = slug
        elif title is not None:
            slug = slugify(title or "")
            if not slug:
                raise serializers.ValidationError({"slug": "Unable to generate slug."})
            attrs["slug"] = slug
        return attrs


class ProductUpdateSerializer(serializers.Serializer):
    title = serializers.CharField(required=False, allow_blank=False)
    slug = serializers.CharField(required=False, allow_blank=False)
    description = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    price = serializers.DecimalField(required=False, max_digits=12, decimal_places=2, min_value=0)
    currency = serializers.CharField(required=False, allow_blank=False)
    category = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class BulkUpdateOperationSerializer(serializers.Serializer):
    type = serializers.ChoiceField(
        choices=(
            "set_category",
            "discount_percent",
            "increase_price_fixed",
            "decrease_price_fixed",
        )
    )
    value = serializers.DecimalField(required=False, max_digits=12, decimal_places=2)
    category_id = serializers.CharField(required=False, allow_null=True, allow_blank=True)


class BulkUpdateSerializer(serializers.Serializer):
    product_ids = serializers.ListField(
        child=serializers.CharField(allow_blank=False),
        allow_empty=False,
    )
    operation = BulkUpdateOperationSerializer()

    def validate_product_ids(self, value):
        if len(value) > 100:
            raise serializers.ValidationError("Maximum 100 product_ids allowed.")
        return value

    def validate(self, attrs):
        operation = attrs.get("operation") or {}
        op_type = operation.get("type")
        value = operation.get("value")
        if op_type == "set_category":
            return attrs
        if value is None:
            raise serializers.ValidationError({"operation": {"value": "This field is required."}})
        if op_type == "discount_percent":
            if value <= 0 or value >= 100:
                raise serializers.ValidationError(
                    {"operation": {"value": "Must be between 0 and 100."}}
                )
        if op_type in {"increase_price_fixed", "decrease_price_fixed"} and value < 0:
            raise serializers.ValidationError(
                {"operation": {"value": "Must be greater than or equal to 0."}}
            )
        return attrs
