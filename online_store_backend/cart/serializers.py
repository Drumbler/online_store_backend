from decimal import Decimal

from rest_framework import serializers

from .models import Cart
from .models import CartItem


class CartItemSerializer(serializers.ModelSerializer):
    product_title_snapshot = serializers.CharField(required=False, allow_blank=True)
    unit_price_snapshot = serializers.DecimalField(
        max_digits=10,
        decimal_places=2,
        required=False,
    )

    class Meta:
        model = CartItem
        fields = [
            "id",
            "product_id",
            "product_title_snapshot",
            "unit_price_snapshot",
            "quantity",
            "created_at",
            "updated_at",
        ]
        read_only_fields = ["id", "created_at", "updated_at"]

    def validate_quantity(self, value):
        if value <= 0:
            raise serializers.ValidationError("Quantity must be greater than 0.")
        return value


class CartSerializer(serializers.ModelSerializer):
    items = CartItemSerializer(many=True, read_only=True)
    total_quantity = serializers.SerializerMethodField()
    total_price = serializers.SerializerMethodField()

    class Meta:
        model = Cart
        fields = [
            "id",
            "items",
            "created_at",
            "updated_at",
            "total_quantity",
            "total_price",
        ]
        read_only_fields = fields

    def get_total_quantity(self, obj):
        return sum(item.quantity for item in obj.items.all())

    def get_total_price(self, obj):
        total = sum(
            (item.unit_price_snapshot * item.quantity for item in obj.items.all()),
            Decimal("0.00"),
        )
        return total
