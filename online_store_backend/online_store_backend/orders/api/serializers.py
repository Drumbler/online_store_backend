from decimal import Decimal

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
            "unit_price_original",
            "discount_percent",
            "unit_price_final",
            "unit_price_snapshot",
            "currency_snapshot",
            "image_url_snapshot",
            "quantity",
            "line_total",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields


class OrderSerializer(serializers.ModelSerializer):
    items = OrderItemSerializer(many=True, read_only=True)
    order_number = serializers.IntegerField(source="id", read_only=True)
    subtotal_original = serializers.SerializerMethodField()
    discount_total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "status",
            "total",
            "subtotal_original",
            "discount_total",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_subtotal_original(self, obj):
        subtotal = sum(
            (item.unit_price_original * item.quantity for item in obj.items.all()),
            Decimal("0.00"),
        )
        return subtotal

    def get_discount_total(self, obj):
        subtotal_original = self.get_subtotal_original(obj)
        return subtotal_original - obj.total


class OrderLookupItemSerializer(serializers.ModelSerializer):
    title_snapshot = serializers.CharField(source="product_title_snapshot", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "title_snapshot",
            "quantity",
            "unit_price_original",
            "discount_percent",
            "unit_price_final",
            "unit_price_snapshot",
            "line_total",
        ]
        read_only_fields = fields


class OrderLookupSerializer(serializers.ModelSerializer):
    order_number = serializers.IntegerField(source="id", read_only=True)
    total_price = serializers.DecimalField(source="total", max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.SerializerMethodField()
    items = OrderLookupItemSerializer(many=True, read_only=True)
    subtotal_original = serializers.SerializerMethodField()
    discount_total = serializers.SerializerMethodField()

    class Meta:
        model = Order
        fields = [
            "order_number",
            "status",
            "created_at",
            "total_price",
            "subtotal_original",
            "discount_total",
            "currency",
            "items",
        ]
        read_only_fields = fields

    def get_currency(self, obj):
        item = obj.items.first()
        return item.currency_snapshot if item else ""

    def get_subtotal_original(self, obj):
        subtotal = sum(
            (item.unit_price_original * item.quantity for item in obj.items.all()),
            Decimal("0.00"),
        )
        return subtotal

    def get_discount_total(self, obj):
        subtotal_original = self.get_subtotal_original(obj)
        return subtotal_original - obj.total
