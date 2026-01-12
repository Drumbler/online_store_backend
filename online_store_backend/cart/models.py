from django.conf import settings
from django.db import models
from django.db.models import Q


class CartStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    CHECKED_OUT = "checked_out", "Checked out"


class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE)
    status = models.CharField(max_length=32, choices=CartStatus.choices, default=CartStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status=CartStatus.ACTIVE),
                name="unique_active_cart_per_user",
            )
        ]

    def __str__(self) -> str:
        return f"Cart #{self.pk} ({self.user})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product_id = models.CharField(max_length=255)
    product_title_snapshot = models.CharField(max_length=255, blank=True)
    unit_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    quantity = models.PositiveIntegerField()
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["cart", "product_id"],
                name="unique_cart_product_id",
            )
        ]

    def __str__(self) -> str:
        return f"{self.product_id} x {self.quantity}"
