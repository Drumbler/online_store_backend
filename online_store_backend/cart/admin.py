from django.contrib import admin

from online_store_backend.cart.models import Cart, CartItem


@admin.register(Cart)
class CartAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "created_at", "updated_at")
    list_filter = ("status",)
    search_fields = ("user__email", "user__username")


@admin.register(CartItem)
class CartItemAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "cart",
        "product_id",
        "product_title_snapshot",
        "unit_price_snapshot",
        "quantity",
        "created_at",
        "updated_at",
    )
    search_fields = ("product_id", "product_title_snapshot")
