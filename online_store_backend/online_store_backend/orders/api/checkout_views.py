from decimal import Decimal
from decimal import InvalidOperation

from django.db import transaction
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from online_store_backend.cart.models import CartStatus
from online_store_backend.cart.utils import get_active_cart
from online_store_backend.integrations.models import IntegrationConfig
from online_store_backend.integrations.models import IntegrationKind
from online_store_backend.integrations.providers import get_shipping_providers
from online_store_backend.integrations.providers import ShippingProviderResponseError
from online_store_backend.integrations.providers import ShippingProviderUnavailableError
from online_store_backend.products.strapi_client import StrapiNotFoundError
from online_store_backend.products.strapi_client import StrapiUnavailableError
from online_store_backend.products.strapi_client import get_product

from ..models import Order
from ..models import OrderItem
from ..models import OrderStatus
from ..pricing import clamp_discount_percent
from ..pricing import compute_discounted_unit_price
from ..pricing import compute_line_total

ADDRESS_REQUIRED_FIELDS = ("city", "street", "house")
ALLOWED_SHIPPING_TYPES = {"pickup", "courier"}


class CheckoutRequestSerializer(serializers.Serializer):
    address = serializers.DictField()
    shipping_provider = serializers.CharField()
    shipping_type = serializers.CharField()
    pickup_point_id = serializers.CharField(required=False, allow_blank=False)
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ShippingQuoteRequestSerializer(serializers.Serializer):
    address = serializers.DictField()
    shipping_type = serializers.CharField()
    pickup_point_id = serializers.CharField(required=False, allow_blank=False)
    comment = serializers.CharField(required=False, allow_blank=True, allow_null=True)


class ShippingPickupPointsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request, provider_id):
        city = (request.query_params.get("city") or "").strip()
        query = (request.query_params.get("q") or "").strip()
        provider = get_shipping_providers().get(provider_id)
        if not provider:
            return Response({"detail": "Shipping provider not found."}, status=status.HTTP_404_NOT_FOUND)

        config = IntegrationConfig.objects.filter(
            kind=IntegrationKind.SHIPPING,
            provider_id=provider_id,
            enabled=True,
        ).first()
        try:
            if provider_id == "yandex_ndd":
                if not config:
                    return Response({"detail": "Shipping provider is disabled."}, status=status.HTTP_400_BAD_REQUEST)
                points = provider.get_pickup_points(city=city, query=query, config=config)
                return Response({"results": points or []}, status=status.HTTP_200_OK)

            points = provider.get_pickup_points(city=city, query=query)
            return Response(points or [], status=status.HTTP_200_OK)
        except ShippingProviderUnavailableError:
            return Response({"detail": "Shipping provider is temporarily unavailable."}, status=status.HTTP_502_BAD_GATEWAY)
        except ShippingProviderResponseError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)


def _validate_address(address, shipping_type: str):
    if not isinstance(address, dict):
        raise serializers.ValidationError({"address": ["Address must be an object."]})

    errors = {}
    for field in ADDRESS_REQUIRED_FIELDS:
        value = address.get(field)
        if value in (None, ""):
            errors[f"address.{field}"] = ["Required"]
    if shipping_type == "courier" and address.get("postal_code") in (None, ""):
        errors["address.postal_code"] = ["Required"]
    if errors:
        raise serializers.ValidationError(errors)


def _validate_shipping_choice(shipping_type: str, pickup_point_id: str | None):
    if shipping_type not in ALLOWED_SHIPPING_TYPES:
        raise serializers.ValidationError({"shipping_type": ["Invalid shipping type."]})
    if shipping_type == "pickup" and not pickup_point_id:
        raise serializers.ValidationError({"pickup_point_id": ["Required for pickup shipping type."]})


def _get_shipping_adapter_and_config(provider_id: str):
    adapter = get_shipping_providers().get(provider_id)
    if not adapter:
        raise serializers.ValidationError({"detail": ["Shipping provider not found."]})

    config = IntegrationConfig.objects.filter(
        kind=IntegrationKind.SHIPPING,
        provider_id=provider_id,
        enabled=True,
    ).first()
    if not config:
        raise serializers.ValidationError({"detail": ["Shipping provider is disabled."]})

    return adapter, config


def _build_priced_items(cart_items):
    priced_items = []
    items_total = Decimal("0.00")
    currency = "RUB"

    for item in cart_items:
        try:
            product = get_product(item.product_id)
        except StrapiNotFoundError:
            raise serializers.ValidationError({"detail": [f"Product {item.product_id} not found."]})
        except StrapiUnavailableError:
            raise serializers.ValidationError({"detail": ["Catalog service unavailable"]})

        try:
            unit_price_original = Decimal(product.get("price", "0.00"))
        except (InvalidOperation, TypeError):
            raise serializers.ValidationError({"detail": ["Catalog service unavailable"]})

        discount_percent = clamp_discount_percent(product.get("discount_percent", 0))
        unit_price_final = compute_discounted_unit_price(unit_price_original, discount_percent)
        line_total = compute_line_total(unit_price_final, item.quantity)

        if product.get("currency"):
            currency = product.get("currency")

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
        items_total += line_total

    return priced_items, items_total, currency


def _shipping_quote(
    provider_id: str,
    shipping_type: str,
    address: dict,
    pickup_point_id: str | None,
    items_total: Decimal,
    items_count: int,
):
    adapter, config = _get_shipping_adapter_and_config(provider_id)
    quote = adapter.quote(
        order_data={"items_total": str(items_total), "items_count": int(items_count or 1)},
        address=address,
        shipping_type=shipping_type,
        pickup_point_id=pickup_point_id,
        config=config,
    )
    try:
        shipping_price_raw = quote.get("shipping_price")
        if shipping_price_raw is None and isinstance(quote.get("offers"), list) and quote["offers"]:
            shipping_price_raw = quote["offers"][0].get("price")
        shipping_price = Decimal(str(shipping_price_raw or "0.00")).quantize(Decimal("0.01"))
    except (InvalidOperation, TypeError, ValueError):
        raise serializers.ValidationError({"detail": ["Shipping provider quote is invalid."]})

    return shipping_price


class CheckoutPreviewView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        address = data["address"]
        shipping_provider = data["shipping_provider"]
        shipping_type = data["shipping_type"]
        pickup_point_id = data.get("pickup_point_id")

        try:
            _validate_shipping_choice(shipping_type, pickup_point_id)
            _validate_address(address, shipping_type)
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        cart = get_active_cart(request)
        if not cart:
            return Response({"detail": "Active cart not found."}, status=status.HTTP_400_BAD_REQUEST)

        cart_items = list(cart.items.all())
        if not cart_items:
            return Response({"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            _, items_total, currency = _build_priced_items(cart_items)
            shipping_price = _shipping_quote(
                provider_id=shipping_provider,
                shipping_type=shipping_type,
                address=address,
                pickup_point_id=pickup_point_id,
                items_total=items_total,
                items_count=len(cart_items),
            )
        except ShippingProviderUnavailableError:
            return Response({"detail": "Shipping provider is temporarily unavailable."}, status=status.HTTP_502_BAD_GATEWAY)
        except ShippingProviderResponseError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except serializers.ValidationError as exc:
            detail = exc.detail
            status_code = status.HTTP_400_BAD_REQUEST
            if "detail" in detail and "not found" in str(detail["detail"][0]).lower():
                status_code = status.HTTP_404_NOT_FOUND
            return Response(detail, status=status_code)

        total = (items_total + shipping_price).quantize(Decimal("0.01"))
        return Response(
            {
                "items_total": float(items_total),
                "shipping_price": float(shipping_price),
                "total": float(total),
                "currency": currency,
            },
            status=status.HTTP_200_OK,
        )


class CheckoutConfirmView(APIView):
    permission_classes = [AllowAny]

    def post(self, request):
        serializer = CheckoutRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        address = data["address"]
        shipping_provider = data["shipping_provider"]
        shipping_type = data["shipping_type"]
        pickup_point_id = data.get("pickup_point_id")

        try:
            _validate_shipping_choice(shipping_type, pickup_point_id)
            _validate_address(address, shipping_type)
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        cart = get_active_cart(request)
        if not cart:
            return Response({"detail": "Active cart not found."}, status=status.HTTP_400_BAD_REQUEST)

        cart_items = list(cart.items.all())
        if not cart_items:
            return Response({"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            priced_items, items_total, currency = _build_priced_items(cart_items)
            shipping_price = _shipping_quote(
                provider_id=shipping_provider,
                shipping_type=shipping_type,
                address=address,
                pickup_point_id=pickup_point_id,
                items_total=items_total,
                items_count=len(cart_items),
            )
        except ShippingProviderUnavailableError:
            return Response({"detail": "Shipping provider is temporarily unavailable."}, status=status.HTTP_502_BAD_GATEWAY)
        except ShippingProviderResponseError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except serializers.ValidationError as exc:
            detail = exc.detail
            status_code = status.HTTP_400_BAD_REQUEST
            if "detail" in detail and "not found" in str(detail["detail"][0]).lower():
                status_code = status.HTTP_404_NOT_FOUND
            return Response(detail, status=status_code)

        total = (items_total + shipping_price).quantize(Decimal("0.01"))

        with transaction.atomic():
            order = Order.objects.create(
                status=OrderStatus.PENDING_PAYMENT,
                total=total,
                shipping_provider=shipping_provider,
                shipping_type=shipping_type,
                shipping_price=shipping_price,
                shipping_address=address,
                pickup_point_id=pickup_point_id,
            )
            if request.user.is_authenticated:
                order.user = request.user
                order.save(update_fields=["user"])

            order_items = []
            for priced in priced_items:
                item = priced["item"]
                product = priced["product"]
                line_total = priced["line_total"]
                order_items.append(
                    OrderItem(
                        order=order,
                        product_id=item.product_id,
                        product_title_snapshot=product.get("title") or item.product_title_snapshot,
                        unit_price_original=priced["unit_price_original"],
                        discount_percent=priced["discount_percent"],
                        unit_price_final=priced["unit_price_final"],
                        unit_price=priced["unit_price_final"],
                        unit_price_snapshot=priced["unit_price_final"],
                        currency_snapshot=product.get("currency") or item.currency_snapshot,
                        image_url_snapshot=product.get("image_url") or item.image_url_snapshot,
                        quantity=item.quantity,
                        line_total=line_total,
                    )
                )

            OrderItem.objects.bulk_create(order_items)

            cart.status = CartStatus.CHECKED_OUT
            cart.save(update_fields=["status", "updated_at"])

        return Response(
            {
                "order_number": order.id,
                "order_secret": order.order_secret,
                "status": order.status,
                "total": float(order.total),
                "currency": currency,
            },
            status=status.HTTP_201_CREATED,
        )


class CheckoutShippingMethodsView(APIView):
    permission_classes = [AllowAny]

    def get(self, request):
        providers = get_shipping_providers()
        enabled_configs = IntegrationConfig.objects.filter(kind=IntegrationKind.SHIPPING, enabled=True)

        results = []
        for config in enabled_configs:
            adapter = providers.get(config.provider_id)
            if not adapter:
                continue
            results.append(
                {
                    "provider_id": config.provider_id,
                    "title": config.display_name or adapter.title,
                    "is_sandbox": config.is_sandbox,
                }
            )
        return Response({"results": results}, status=status.HTTP_200_OK)


class ShippingQuoteView(APIView):
    permission_classes = [AllowAny]

    def post(self, request, provider_id):
        serializer = ShippingQuoteRequestSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        address = data["address"]
        shipping_type = data["shipping_type"]
        pickup_point_id = data.get("pickup_point_id")

        try:
            _validate_shipping_choice(shipping_type, pickup_point_id)
            _validate_address(address, shipping_type)
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        cart = get_active_cart(request)
        if not cart:
            return Response({"detail": "Active cart not found."}, status=status.HTTP_400_BAD_REQUEST)

        cart_items = list(cart.items.all())
        if not cart_items:
            return Response({"detail": "Cart is empty."}, status=status.HTTP_400_BAD_REQUEST)

        try:
            _, items_total, _ = _build_priced_items(cart_items)
            adapter, config = _get_shipping_adapter_and_config(provider_id)
            quote = adapter.quote(
                order_data={"items_total": str(items_total), "items_count": len(cart_items)},
                address=address,
                shipping_type=shipping_type,
                pickup_point_id=pickup_point_id,
                config=config,
            )
        except ShippingProviderUnavailableError:
            return Response({"detail": "Shipping provider is temporarily unavailable."}, status=status.HTTP_502_BAD_GATEWAY)
        except ShippingProviderResponseError as exc:
            return Response({"detail": str(exc)}, status=status.HTTP_400_BAD_REQUEST)
        except serializers.ValidationError as exc:
            detail = exc.detail
            status_code = status.HTTP_400_BAD_REQUEST
            if "detail" in detail and "not found" in str(detail["detail"][0]).lower():
                status_code = status.HTTP_404_NOT_FOUND
            return Response(detail, status=status_code)

        offers = quote.get("offers")
        if not isinstance(offers, list):
            offers = []

        return Response({"offers": offers}, status=status.HTTP_200_OK)
