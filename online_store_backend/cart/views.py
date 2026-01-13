from decimal import Decimal

from rest_framework import mixins
from rest_framework import status
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from .models import Cart
from .models import CartItem
from .models import CartStatus
from .serializers import CartItemSerializer
from .serializers import CartSerializer


class CartView(APIView):
    permission_classes = [IsAuthenticated]

    def get(self, request):
        cart, _ = Cart.objects.get_or_create(user=request.user, status=CartStatus.ACTIVE)
        serializer = CartSerializer(cart, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CartItemViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, GenericViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [IsAuthenticated]

    def get_queryset(self):
        return CartItem.objects.filter(
            cart__user=self.request.user,
            cart__status=CartStatus.ACTIVE,
        )

    def _get_or_create_cart(self):
        cart, _ = Cart.objects.get_or_create(user=self.request.user, status=CartStatus.ACTIVE)
        return cart

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        cart = self._get_or_create_cart()
        product_id = data["product_id"]
        quantity = data["quantity"]
        title_provided = "product_title_snapshot" in data
        price_provided = "unit_price_snapshot" in data
        title = data.get("product_title_snapshot", "")
        unit_price = data.get("unit_price_snapshot", Decimal("0.00"))

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product_id=product_id,
            defaults={
                "product_title_snapshot": title,
                "unit_price_snapshot": unit_price,
                "quantity": quantity,
            },
        )
        if not created:
            item.quantity += quantity
            update_fields = ["quantity", "updated_at"]
            if title_provided:
                item.product_title_snapshot = title
                update_fields.append("product_title_snapshot")
            if price_provided:
                item.unit_price_snapshot = unit_price
                update_fields.append("unit_price_snapshot")
            item.save(update_fields=update_fields)

        output_serializer = self.get_serializer(item)
        return Response(
            output_serializer.data,
            status=status.HTTP_201_CREATED if created else status.HTTP_200_OK,
        )

    def update(self, request, *args, **kwargs):
        item = self.get_object()
        serializer = self.get_serializer(item, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        item.quantity = serializer.validated_data["quantity"]
        item.save(update_fields=["quantity", "updated_at"])
        return Response(self.get_serializer(item).data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
