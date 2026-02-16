from decimal import Decimal

from django.conf import settings
from django.db import models


class OrderStatus(models.TextChoices):
    PENDING = "pending", "Pending"
    PAID = "paid", "Paid"
    CANCELLED = "cancelled", "Cancelled"


class Order(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="orders", null=True, blank=True)
    status = models.CharField(max_length=32, choices=OrderStatus.choices, default=OrderStatus.PENDING)
    total = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]

    def __str__(self) -> str:
        return f"Order #{self.pk} ({self.user})"


class OrderItem(models.Model):
    order = models.ForeignKey(Order, on_delete=models.CASCADE, related_name="items")
    product_id = models.CharField(max_length=255)
    product_title_snapshot = models.CharField(max_length=255, blank=True)
    unit_price_original = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    discount_percent = models.PositiveSmallIntegerField(default=0)
    unit_price_final = models.DecimalField(max_digits=10, decimal_places=2, default=Decimal("0.00"))
    unit_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    currency_snapshot = models.CharField(max_length=16, blank=True)
    image_url_snapshot = models.URLField(max_length=1000, blank=True)
    quantity = models.PositiveIntegerField()
    line_total = models.DecimalField(max_digits=10, decimal_places=2)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    def __str__(self) -> str:
        return f"{self.product_id} x {self.quantity}"
