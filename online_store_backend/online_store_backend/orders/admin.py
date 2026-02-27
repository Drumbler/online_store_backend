from django.contrib import admin

from .models import Order
from .models import OrderItem
from .models import ProductViewEvent
from .models import Review


@admin.register(Order)
class OrderAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "status", "total", "order_secret", "created_at")
    list_filter = ("status", "created_at")
    search_fields = ("id", "order_secret", "user__email")


@admin.register(OrderItem)
class OrderItemAdmin(admin.ModelAdmin):
    list_display = ("id", "order", "product_id", "quantity", "line_total", "review_left_at")
    search_fields = ("product_id", "order__id", "review_token")


@admin.register(Review)
class ReviewAdmin(admin.ModelAdmin):
    list_display = ("id", "product_id", "order", "rating", "author_display_name", "created_at")
    list_filter = ("rating", "is_anonymous", "created_at")
    search_fields = ("product_id", "order__id", "author_display_name")


@admin.register(ProductViewEvent)
class ProductViewEventAdmin(admin.ModelAdmin):
    list_display = ("id", "product_id", "viewed_at")
    search_fields = ("product_id",)
    list_filter = ("viewed_at",)
