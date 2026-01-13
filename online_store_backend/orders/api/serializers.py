from rest_framework import serializers

from ..models import Order
from ..models import OrderItem


class OrderItemSerializer(serializers.ModelSerializer):
    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_id",
            "product_title_snapshot",
            "unit_price_snapshot",
            "quantity",
            "line_total",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "status",
            "total",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields
