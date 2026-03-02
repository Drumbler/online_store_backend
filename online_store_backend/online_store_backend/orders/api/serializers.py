"""Сериализаторы API заказов и отзывов."""

from decimal import Decimal

from rest_framework import serializers

from ..models import Order
from ..models import OrderItem
from ..models import Review


class OrderItemSerializer(serializers.ModelSerializer):
    """Read-only сериализатор позиции заказа."""

    class Meta:
        model = OrderItem
        fields = [
            "id",
            "product_id",
            "product_title_snapshot",
            "unit_price_original",
            "discount_percent",
            "unit_price_final",
            "unit_price",
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
    """Основной сериализатор заказа для личного кабинета."""

    items = OrderItemSerializer(many=True, read_only=True)
    order_number = serializers.IntegerField(source="id", read_only=True)
    order_secret = serializers.CharField(read_only=True)
    subtotal_original = serializers.SerializerMethodField()
    items_total = serializers.SerializerMethodField()
    discount_total = serializers.SerializerMethodField()
    shipping_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = [
            "id",
            "order_number",
            "order_secret",
            "status",
            "total",
            "subtotal_original",
            "items_total",
            "discount_total",
            "shipping_price",
            "items",
            "created_at",
            "updated_at",
        ]
        read_only_fields = fields

    def get_subtotal_original(self, obj):
        """Считает сумму позиций без учета скидок."""
        subtotal = sum(
            (item.unit_price_original * item.quantity for item in obj.items.all()),
            Decimal("0.00"),
        )
        return subtotal

    def get_items_total(self, obj):
        """Считает итог по позициям после скидок."""
        items_total = sum(
            (item.line_total for item in obj.items.all()),
            Decimal("0.00"),
        )
        return items_total

    def get_discount_total(self, obj):
        """Вычисляет абсолютную сумму скидки заказа."""
        subtotal_original = self.get_subtotal_original(obj)
        return subtotal_original - self.get_items_total(obj)


class OrderLookupItemSerializer(serializers.ModelSerializer):
    """Позиция заказа для публичного lookup-ответа."""

    title_snapshot = serializers.CharField(source="product_title_snapshot", read_only=True)

    class Meta:
        model = OrderItem
        fields = [
            "title_snapshot",
            "quantity",
            "unit_price_original",
            "discount_percent",
            "unit_price_final",
            "unit_price",
            "unit_price_snapshot",
            "line_total",
        ]
        read_only_fields = fields


class OrderLookupSerializer(serializers.ModelSerializer):
    """Сериализатор публичного просмотра заказа по номеру и секрету."""

    order_number = serializers.IntegerField(source="id", read_only=True)
    order_secret = serializers.CharField(read_only=True)
    total_price = serializers.DecimalField(source="total", max_digits=10, decimal_places=2, read_only=True)
    currency = serializers.SerializerMethodField()
    items = OrderLookupItemSerializer(many=True, read_only=True)
    subtotal_original = serializers.SerializerMethodField()
    items_total = serializers.SerializerMethodField()
    discount_total = serializers.SerializerMethodField()
    shipping_price = serializers.DecimalField(max_digits=10, decimal_places=2, read_only=True)

    class Meta:
        model = Order
        fields = [
            "order_number",
            "order_secret",
            "status",
            "created_at",
            "total_price",
            "subtotal_original",
            "items_total",
            "discount_total",
            "shipping_price",
            "currency",
            "items",
        ]
        read_only_fields = fields

    def get_currency(self, obj):
        """Определяет валюту по первой позиции заказа."""
        item = obj.items.first()
        return item.currency_snapshot if item else ""

    def get_subtotal_original(self, obj):
        """Считает сумму позиций без учета скидок."""
        subtotal = sum(
            (item.unit_price_original * item.quantity for item in obj.items.all()),
            Decimal("0.00"),
        )
        return subtotal

    def get_items_total(self, obj):
        """Считает итог по позициям после скидок."""
        items_total = sum(
            (item.line_total for item in obj.items.all()),
            Decimal("0.00"),
        )
        return items_total

    def get_discount_total(self, obj):
        """Вычисляет абсолютную сумму скидки заказа."""
        subtotal_original = self.get_subtotal_original(obj)
        return subtotal_original - self.get_items_total(obj)


class ReviewSerializer(serializers.ModelSerializer):
    """Read-only сериализатор опубликованного отзыва."""

    class Meta:
        model = Review
        fields = [
            "id",
            "rating",
            "pros",
            "cons",
            "comment",
            "author_display_name",
            "created_at",
        ]
        read_only_fields = fields


class ReviewCreateSerializer(serializers.Serializer):
    """Входные данные для создания отзыва после покупки."""

    review_token = serializers.CharField()
    rating = serializers.IntegerField(min_value=1, max_value=5)
    pros = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    cons = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)
    is_anonymous = serializers.BooleanField(default=False)


class EligibleReviewProductSerializer(serializers.Serializer):
    """Товар, доступный для оставления отзыва пользователем."""

    product_id = serializers.CharField()
    title = serializers.CharField(allow_blank=True)
    image_url = serializers.CharField(allow_blank=True, allow_null=True)
    review_token = serializers.CharField()
