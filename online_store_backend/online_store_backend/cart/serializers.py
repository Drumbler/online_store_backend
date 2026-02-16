from decimal import Decimal

from rest_framework import serializers

from .models import CartItem


class CartItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = CartItem
        fields = [
            "id",
            "product_id",
            "product_title_snapshot",
            "unit_price_snapshot",
            "currency_snapshot",
            "image_url_snapshot",
            "quantity",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class CartItemCreateSerializer(serializers.Serializer):
    product_id = serializers.CharField()
    quantity = serializers.IntegerField(min_value=1)


class CartItemUpdateSerializer(serializers.Serializer):
    quantity = serializers.IntegerField(min_value=1)


class CartProductSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    slug = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    image_url = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    thumbnail_url = serializers.CharField(allow_blank=True, allow_null=True, required=False)
    currency = serializers.CharField(allow_blank=True, allow_null=True, required=False)


class CartPricingItemSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    product = CartProductSerializer()
    quantity = serializers.IntegerField(min_value=1)
    unit_price_original = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount_percent = serializers.IntegerField(min_value=0, max_value=100)
    unit_price_final = serializers.DecimalField(max_digits=12, decimal_places=2)
    line_total = serializers.DecimalField(max_digits=12, decimal_places=2)


class CartSerializer(serializers.Serializer):
    id = serializers.IntegerField()
    items = CartPricingItemSerializer(many=True)
    created_at = serializers.DateTimeField()
    updated_at = serializers.DateTimeField()
    total_quantity = serializers.IntegerField()
    subtotal_original = serializers.DecimalField(max_digits=12, decimal_places=2)
    subtotal_final = serializers.DecimalField(max_digits=12, decimal_places=2)
    discount_total = serializers.DecimalField(max_digits=12, decimal_places=2)
    total = serializers.DecimalField(max_digits=12, decimal_places=2)
    total_price = serializers.SerializerMethodField()

    def get_total_price(self, obj: dict):
        return obj.get("total", Decimal("0.00"))
