"""Модели заказов, оплат, отзывов и событий просмотров."""

from decimal import Decimal
import secrets
import string

from django.conf import settings
from django.db import models


def _random_token(length: int) -> str:
    """Генерирует случайный алфавитно-цифровой токен заданной длины."""
    alphabet = string.ascii_letters + string.digits
    return "".join(secrets.choice(alphabet) for _ in range(length))


def generate_order_secret() -> str:
    """Генерирует короткий секрет для публичного lookup заказа."""
    return _random_token(12)


def generate_review_token() -> str:
    """Генерирует токен для подтверждения права оставить отзыв."""
    return _random_token(24)


class OrderStatus(models.TextChoices):
    """Допустимые статусы жизненного цикла заказа."""

    PENDING_PAYMENT = "pending_payment", "Pending payment"
    PAID = "paid", "Paid"
    PAYMENT_FAILED = "payment_failed", "Payment failed"
    CANCELLED = "cancelled", "Cancelled"


class OrderDeliveryStatus(models.TextChoices):
    """Статусы логистики заказа для синхронизации с внешним сервисом доставки."""

    AWAITING_PAYMENT = "awaiting_payment", "Awaiting payment"
    READY_FOR_DISPATCH = "ready_for_dispatch", "Ready for dispatch"
    HANDOVER_TO_DELIVERY = "handover_to_delivery", "Handed over to delivery"
    IN_TRANSIT = "in_transit", "In transit"
    READY_FOR_PICKUP = "ready_for_pickup", "Ready for pickup"
    DELIVERED = "delivered", "Delivered"
    DELIVERY_FAILED = "delivery_failed", "Delivery failed"
    CANCELLED = "cancelled", "Cancelled"


class Order(models.Model):
    """Заказ пользователя или гостя с итоговой стоимостью и доставкой."""

    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders", null=True, blank=True)
    order_secret = models.CharField(max_length=32, default=generate_order_secret)
    status = models.CharField(max_length=32, choices=OrderStatus.choices, default=OrderStatus.PENDING_PAYMENT)
    paid_at = models.DateTimeField(null=True, blank=True)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    shipping_provider = models.CharField(max_length=64, null=True, blank=True)
    shipping_type = models.CharField(max_length=32, null=True, blank=True)
    shipping_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    shipping_address = models.JSONField(null=True, blank=True)
    pickup_point_id = models.CharField(max_length=128, null=True, blank=True)
    delivery_status = models.CharField(
        max_length=32,
        choices=OrderDeliveryStatus.choices,
        default=OrderDeliveryStatus.AWAITING_PAYMENT,
    )
    delivery_external_id = models.CharField(max_length=128, null=True, blank=True)
    delivery_tracking_number = models.CharField(max_length=128, null=True, blank=True)
    delivery_status_note = models.CharField(max_length=255, blank=True, default="")
    delivery_last_event_at = models.DateTimeField(null=True, blank=True)
    delivery_last_payload = models.JSONField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order #{self.pk} ({self.user})"


class OrderItem(models.Model):
    """Позиция товара в заказе со snapshot-данными цены/названия."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    review_token = models.CharField(max_length=64, unique=True, default=generate_review_token)
    review_left_at = models.DateTimeField(null=True, blank=True)
    product_id = models.CharField(max_length=255)
    product_title_snapshot = models.CharField(max_length=255, blank=True)
    unit_price_original = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount_percent = models.PositiveSmallIntegerField(default=0)
    unit_price_final = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    unit_price = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    unit_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    currency_snapshot = models.CharField(max_length=16, blank=True)
    image_url_snapshot = models.URLField(max_length=1000, blank=True)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.product_id} x {self.quantity}"


class ProductViewEvent(models.Model):
    """Событие просмотра карточки товара для отчетов и аналитики."""

    product_id = models.CharField(max_length=255)
    viewed_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-viewed_at"]
        indexes = [
            models.Index(fields=["product_id", "viewed_at"], name="orders_pve_pid_viewed_idx"),
        ]

    def __str__(self) -> str:
        return f"ProductViewEvent(product={self.product_id}, at={self.viewed_at})"


class Review(models.Model):
    """Отзыв по конкретному товару в рамках заказа."""

    product_id = models.CharField(max_length=255)
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="reviews")
    rating = models.PositiveSmallIntegerField()
    pros = models.TextField(blank=True)
    cons = models.TextField(blank=True)
    comment = models.TextField(blank=True)
    is_anonymous = models.BooleanField(default=False)
    author_user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="reviews",
        null=True,
        blank=True,
    )
    author_display_name = models.CharField(max_length=255)
    is_published = models.BooleanField(default=True)
    moderated_at = models.DateTimeField(null=True, blank=True)
    moderated_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.SET_NULL,
        related_name="moderated_reviews",
        null=True,
        blank=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["product_id", "created_at"]),
            models.Index(fields=["order"]),
        ]

    def __str__(self) -> str:
        return f"Review({self.product_id}, rating={self.rating})"


class PaymentStatus(models.TextChoices):
    """Статусы операций оплаты."""

    PENDING = "pending", "Pending"
    SUCCEEDED = "succeeded", "Succeeded"
    FAILED = "failed", "Failed"


class Payment(models.Model):
    """Транзакция оплаты заказа через выбранного провайдера."""

    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="payments")
    provider_id = models.CharField(max_length=64)
    status = models.CharField(max_length=32, choices=PaymentStatus.choices, default=PaymentStatus.PENDING)
    amount = models.DecimalField(max_digits=10, decimal_places=2)
    currency = models.CharField(max_length=16, default="RUB")
    external_id = models.CharField(max_length=255, null=True, blank=True)
    payment_url = models.TextField(null=True, blank=True)
    completed_at = models.DateTimeField(null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["order", "status"]),
            models.Index(fields=["provider_id"]),
            models.Index(fields=["external_id"]),
        ]
        constraints = [
            models.UniqueConstraint(
                fields=["order"],
                condition=models.Q(status=PaymentStatus.PENDING),
                name="uniq_pending_payment_per_order",
            ),
        ]

    def __str__(self) -> str:
        return f"Payment({self.id}, order={self.order_id}, provider={self.provider_id}, status={self.status})"
