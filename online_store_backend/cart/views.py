import logging
from decimal import Decimal
from decimal import InvalidOperation

from rest_framework import mixins
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import GenericViewSet

from online_store_backend.products.strapi_client import StrapiNotFoundError
from online_store_backend.products.strapi_client import StrapiUnavailableError
from online_store_backend.products.strapi_client import get_product

from .models import CartItem
from .models import CartStatus
from .serializers import CartItemCreateSerializer
from .serializers import CartItemSerializer
from .serializers import CartItemUpdateSerializer
from .serializers import CartSerializer
from .utils import get_or_create_cart

logger = logging.getLogger(__name__)


class CartView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        cart = get_or_create_cart(request)
        serializer = CartSerializer(cart, context={"request": request})
        return Response(serializer.data, status=status.HTTP_200_OK)


class CartItemViewSet(mixins.CreateModelMixin, mixins.UpdateModelMixin, mixins.DestroyModelMixin, GenericViewSet):
    serializer_class = CartItemSerializer
    permission_classes = [AllowAny]

    def get_serializer_class(self):
        if self.action == "create":
            return CartItemCreateSerializer
        if self.action in {"update", "partial_update"}:
            return CartItemUpdateSerializer
        return CartItemSerializer

    def get_queryset(self):
        cart = get_or_create_cart(self.request)
        return CartItem.objects.filter(
            cart=cart,
            cart__status=CartStatus.ACTIVE,
        )

    def create(self, request, *args, **kwargs):
        serializer = self.get_serializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        product_id = data["product_id"]
        quantity = data["quantity"]

        try:
            product = get_product(product_id)
        except StrapiNotFoundError:
            return Response({"detail": "Product not found."}, status=status.HTTP_404_NOT_FOUND)
        except StrapiUnavailableError:
            logger.exception("Catalog lookup failed for product %s", product_id)
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        try:
            unit_price = Decimal(product.get("price", "0.00"))
        except (InvalidOperation, TypeError):
            logger.error("Invalid price for product %s from catalog", product_id)
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )

        cart = get_or_create_cart(request)
        title = product.get("title") or ""
        currency = product.get("currency") or ""
        image_url = product.get("image_url") or ""

        item, created = CartItem.objects.get_or_create(
            cart=cart,
            product_id=product_id,
            defaults={
                "product_title_snapshot": title,
                "unit_price_snapshot": unit_price,
                "currency_snapshot": currency,
                "image_url_snapshot": image_url,
                "quantity": quantity,
            },
        )
        if not created:
            item.quantity += quantity
            item.product_title_snapshot = title
            item.unit_price_snapshot = unit_price
            item.currency_snapshot = currency
            item.image_url_snapshot = image_url
            item.save(
                update_fields=[
                    "quantity",
                    "product_title_snapshot",
                    "unit_price_snapshot",
                    "currency_snapshot",
                    "image_url_snapshot",
                    "updated_at",
                ]
            )

        output_serializer = CartItemSerializer(item)
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
        return Response(CartItemSerializer(item).data, status=status.HTTP_200_OK)

    def partial_update(self, request, *args, **kwargs):
        return self.update(request, *args, **kwargs)
