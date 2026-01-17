from django.conf import settings
from django.db import models
from django.db.models import Q


class CartStatus(models.TextChoices):
    ACTIVE = "active", "Active"
    CHECKED_OUT = "checked_out", "Checked out"


class Cart(models.Model):
    user = models.ForeignKey(settings.AUTH_USER_MODEL, on_delete=models.CASCADE, null=True, blank=True)
    session_key = models.CharField(max_length=40, null=True, blank=True, db_index=True)
    status = models.CharField(max_length=32, choices=CartStatus.choices, default=CartStatus.ACTIVE)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        constraints = [
            models.UniqueConstraint(
                fields=["user"],
                condition=Q(status=CartStatus.ACTIVE, user__isnull=False),
                name="unique_active_cart_per_user",
            ),
            models.UniqueConstraint(
                fields=["session_key"],
                condition=Q(status=CartStatus.ACTIVE, session_key__isnull=False),
                name="unique_active_cart_per_session",
            ),
        ]

    def __str__(self) -> str:
        return f"Cart #{self.pk} ({self.user})"


class CartItem(models.Model):
    cart = models.ForeignKey(Cart, on_delete=models.CASCADE, related_name="items")
    product_id = models.CharField(max_length=255)
    product_title_snapshot = models.CharField(max_length=255, blank=True)
    unit_price_snapshot = models.DecimalField(max_digits=10, decimal_places=2)
    currency_snapshot = models.CharField(max_length=16, blank=True)
    image_url_snapshot = models.URLField(max_length=1000, blank=True)
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
