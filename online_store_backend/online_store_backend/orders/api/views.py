from decimal import Decimal
from decimal import InvalidOperation

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from online_store_backend.cart.models import CartStatus
from online_store_backend.cart.utils import get_active_cart
from online_store_backend.products.strapi_client import StrapiNotFoundError
from online_store_backend.products.strapi_client import StrapiUnavailableError
from online_store_backend.products.strapi_client import get_product

from ..models import Order
from ..models import OrderItem
from ..models import OrderStatus
from ..pricing import clamp_discount_percent
from ..pricing import compute_discounted_unit_price
from ..pricing import compute_line_total
from .serializers import OrderLookupSerializer
from .serializers import OrderSerializer


class OrderPagination(PageNumberPagination):
    page_size = 20


class OrderViewSet(ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination

    def get_queryset(self):
        user = self.request.user
        if user.is_staff or user.is_superuser:
            return Order.objects.all().prefetch_related("items")
        return Order.objects.filter(user=user).prefetch_related("items")

    @action(
        detail=False,
        methods=["post"],
        url_path="checkout",
        permission_classes=[AllowAny],
    )
    def checkout(self, request):
        cart = get_active_cart(request)
        if not cart:
            return Response({"detail": "Active cart not found."}, status=status.HTTP_400_BAD_REQUEST)

        cart_items = list(cart.items.all())
        if not cart_items:
            return Response({"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        priced_items = []
        for item in cart_items:
            try:
                product = get_product(item.product_id)
            except StrapiNotFoundError:
                return Response(
                    {"detail": f"Product {item.product_id} not found."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            except StrapiUnavailableError:
                return Response(
                    {"detail": "Catalog service unavailable"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )

            try:
                unit_price_original = Decimal(product.get("price", "0.00"))
            except (InvalidOperation, TypeError):
                return Response(
                    {"detail": "Catalog service unavailable"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            discount_percent = clamp_discount_percent(product.get("discount_percent", 0))
            unit_price_final = compute_discounted_unit_price(unit_price_original, discount_percent)
            line_total = compute_line_total(unit_price_final, item.quantity)
            priced_items.append(
                {
                    "item": item,
                    "product": product,
                    "unit_price_original": unit_price_original,
                    "discount_percent": discount_percent,
                    "unit_price_final": unit_price_final,
                    "line_total": line_total,
                }
            )

        with transaction.atomic():
            order = Order.objects.create(status=OrderStatus.PENDING, total=Decimal("0.00"))
            if request.user.is_authenticated:
                order.user = request.user
                order.save(update_fields=["user"])
            order_items = []
            total = Decimal("0.00")

            for priced in priced_items:
                item = priced["item"]
                product = priced["product"]
                line_total = priced["line_total"]
                total += line_total
                order_items.append(
                    OrderItem(
                        order=order,
                        product_id=item.product_id,
                        product_title_snapshot=product.get("title") or item.product_title_snapshot,
                        unit_price_original=priced["unit_price_original"],
                        discount_percent=priced["discount_percent"],
                        unit_price_final=priced["unit_price_final"],
                        unit_price_snapshot=priced["unit_price_final"],
                        currency_snapshot=product.get("currency") or item.currency_snapshot,
                        image_url_snapshot=product.get("image_url") or item.image_url_snapshot,
                        quantity=item.quantity,
                        line_total=line_total,
                    )
                )

            OrderItem.objects.bulk_create(order_items)
            order.total = total
            order.save(update_fields=["total", "updated_at"])

            cart.status = CartStatus.CHECKED_OUT
            cart.save(update_fields=["status", "updated_at"])

            if request.user.is_authenticated and request.user.email:
                from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "no-reply@example.com")

                def _send_confirmation():
                    send_mail(
                        subject=f"Order #{order.id} confirmation",
                        message=f"Thanks for your order. Total: {order.total}.",
                        from_email=from_email,
                        recipient_list=[request.user.email],
                        fail_silently=False,
                    )

                transaction.on_commit(_send_confirmation)

        serializer = self.get_serializer(order)
        return Response(serializer.data, status=status.HTTP_201_CREATED)

    @action(
        detail=False,
        methods=["get"],
        url_path="lookup",
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def lookup(self, request):
        number = request.query_params.get("number")
        if not number:
            return Response({"detail": "Order number is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            order_id = int(number)
        except (TypeError, ValueError):
            return Response({"detail": "Order number is invalid."}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.filter(id=order_id).prefetch_related("items").first()

        if not order:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderLookupSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)
