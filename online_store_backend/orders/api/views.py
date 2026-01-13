from decimal import Decimal

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.viewsets import ReadOnlyModelViewSet

from online_store_backend.cart.models import Cart
from online_store_backend.cart.models import CartStatus

from ..models import Order
from ..models import OrderItem
from ..models import OrderStatus
from .serializers import OrderSerializer


class OrderPagination(PageNumberPagination):
    page_size = 20


class OrderViewSet(ReadOnlyModelViewSet):
    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination

    def get_queryset(self):
        return Order.objects.filter(user=self.request.user).prefetch_related("items")

    @action(detail=False, methods=["post"], url_path="checkout")
    def checkout(self, request):
        cart = (
            Cart.objects.filter(user=request.user, status=CartStatus.ACTIVE)
            .prefetch_related("items")
            .first()
        )
        if not cart:
            return Response({"detail": "Active cart not found."}, status=status.HTTP_400_BAD_REQUEST)

        cart_items = list(cart.items.all())
        if not cart_items:
            return Response({"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        with transaction.atomic():
            order = Order.objects.create(user=request.user, status=OrderStatus.PENDING, total=Decimal("0.00"))
            order_items = []
            total = Decimal("0.00")

            for item in cart_items:
                line_total = item.unit_price_snapshot * item.quantity
                total += line_total
                order_items.append(
                    OrderItem(
                        order=order,
                        product_id=item.product_id,
                        product_title_snapshot=item.product_title_snapshot,
                        unit_price_snapshot=item.unit_price_snapshot,
                        quantity=item.quantity,
                        line_total=line_total,
                    )
                )

            OrderItem.objects.bulk_create(order_items)
            order.total = total
            order.save(update_fields=["total", "updated_at"])

            cart.status = CartStatus.CHECKED_OUT
            cart.save(update_fields=["status", "updated_at"])

            if request.user.email:
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
