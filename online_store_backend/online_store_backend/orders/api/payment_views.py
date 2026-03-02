"""API оплаты: выбор провайдера, создание платежа и обработка webhook."""

import logging
from decimal import Decimal

from django.conf import settings
from django.db import IntegrityError
from django.db import transaction
from django.utils import timezone
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.views import APIView

from online_store_backend.integrations.models import IntegrationConfig
from online_store_backend.integrations.models import IntegrationKind
from online_store_backend.integrations.providers import PaymentProviderUnavailableError
from online_store_backend.integrations.providers import get_payment_providers

from ..models import Order
from ..models import OrderStatus
from ..models import Payment
from ..models import PaymentStatus

logger = logging.getLogger(__name__)


class InvalidPaymentProviderResponseError(Exception):
    """Исключение для невалидного ответа провайдера оплаты."""


class CreatePaymentSerializer(serializers.Serializer):
    """Валидатор запроса на создание платежа по заказу."""

    order_number = serializers.CharField()
    order_secret = serializers.CharField(required=False, allow_blank=False)
    provider_id = serializers.CharField()


class PaymentWebhookSerializer(serializers.Serializer):
    """Валидатор входящих webhook-событий от провайдера оплаты."""

    external_id = serializers.CharField()
    status = serializers.ChoiceField(choices=[PaymentStatus.SUCCEEDED, PaymentStatus.FAILED])


def _resolve_order_for_payment(request, order_number: str, order_secret: str | None):
    """Найти заказ для оплаты с учетом режима гостя и авторизованного пользователя."""
    try:
        order_id = int(order_number)
    except (TypeError, ValueError):
        raise serializers.ValidationError({"order_number": ["Order number is invalid."]})

    order = Order.objects.filter(id=order_id).first()
    if not order:
        raise serializers.ValidationError({"detail": ["Order not found."]})

    user = request.user
    if user.is_authenticated:
        if order.user_id != user.id:
            raise serializers.ValidationError({"detail": ["Order not found."]})
        return order

    if not order_secret:
        raise serializers.ValidationError({"order_secret": ["Order secret is required."]})
    if order.order_secret != order_secret:
        raise serializers.ValidationError({"detail": ["Order not found."]})
    return order


class CheckoutPaymentMethodsView(APIView):
    """Вернуть доступные способы оплаты для checkout."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Получить список активных платежных провайдеров."""
        providers = get_payment_providers()
        enabled_configs = IntegrationConfig.objects.filter(kind=IntegrationKind.PAYMENT, enabled=True)

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


class PaymentCreateView(APIView):
    """Создать платеж для заказа с учетом идемпотентности и статусов."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Инициировать платеж у провайдера и вернуть платежную ссылку."""
        serializer = CreatePaymentSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        provider_id = data["provider_id"]
        providers = get_payment_providers()
        adapter = providers.get(provider_id)
        if not adapter:
            return Response({"detail": "Unknown payment provider."}, status=status.HTTP_404_NOT_FOUND)

        try:
            order = _resolve_order_for_payment(
                request,
                order_number=data["order_number"],
                order_secret=data.get("order_secret"),
            )
        except serializers.ValidationError as exc:
            detail = exc.detail
            status_code = status.HTTP_404_NOT_FOUND if "detail" in detail else status.HTTP_400_BAD_REQUEST
            return Response(detail, status=status_code)

        config = IntegrationConfig.objects.filter(
            kind=IntegrationKind.PAYMENT,
            provider_id=provider_id,
            enabled=True,
        ).first()
        if not config:
            return Response({"detail": "Payment provider is not available."}, status=status.HTTP_400_BAD_REQUEST)

        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173").rstrip("/")
        return_url = f"{frontend_url}/demo-pay"

        try:
            with transaction.atomic():
                locked_order = Order.objects.select_for_update().get(id=order.id)

                if locked_order.status == OrderStatus.PAID:
                    return Response({"detail": "Order is already paid."}, status=status.HTTP_409_CONFLICT)

                existing_pending = (
                    Payment.objects.select_for_update()
                    .filter(order=locked_order, status=PaymentStatus.PENDING)
                    .order_by("-id")
                    .first()
                )
                if existing_pending:
                    logger.info(
                        "Idempotent payment create reuse pending payment",
                        extra={"order_id": locked_order.id, "payment_id": existing_pending.id, "provider_id": provider_id},
                    )
                    return Response(
                        {
                            "payment_id": existing_pending.id,
                            "payment_url": existing_pending.payment_url,
                            "external_id": existing_pending.external_id,
                        },
                        status=status.HTTP_200_OK,
                    )

                if locked_order.status not in {OrderStatus.PENDING_PAYMENT, OrderStatus.PAYMENT_FAILED}:
                    return Response(
                        {"detail": "Order is not available for payment creation."},
                        status=status.HTTP_400_BAD_REQUEST,
                    )

                payment = Payment.objects.create(
                    order=locked_order,
                    provider_id=provider_id,
                    status=PaymentStatus.PENDING,
                    amount=Decimal(locked_order.total),
                    currency="RUB",
                )

                created = adapter.create_payment(order=locked_order, config=config, return_url=return_url)
                payment.payment_url = created.get("payment_url")
                payment.external_id = created.get("external_id")
                if not payment.payment_url or not payment.external_id:
                    logger.error(
                        "Payment provider returned invalid create_payment payload",
                        extra={"order_id": locked_order.id, "payment_id": payment.id, "provider_id": provider_id},
                    )
                    raise InvalidPaymentProviderResponseError

                payment.save(update_fields=["payment_url", "external_id", "updated_at"])

        except PaymentProviderUnavailableError:
            logger.warning(
                "Payment provider unavailable during payment creation",
                extra={"order_id": order.id, "provider_id": provider_id},
            )
            return Response(
                {"detail": "Payment provider is temporarily unavailable."},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except InvalidPaymentProviderResponseError:
            return Response(
                {"detail": "Payment provider returned invalid response."},
                status=status.HTTP_500_INTERNAL_SERVER_ERROR,
            )
        except IntegrityError:
            existing_pending = Payment.objects.filter(order=order, status=PaymentStatus.PENDING).order_by("-id").first()
            if existing_pending:
                logger.info(
                    "Concurrent payment create resolved to existing pending payment",
                    extra={"order_id": order.id, "payment_id": existing_pending.id, "provider_id": provider_id},
                )
                return Response(
                    {
                        "payment_id": existing_pending.id,
                        "payment_url": existing_pending.payment_url,
                        "external_id": existing_pending.external_id,
                    },
                    status=status.HTTP_200_OK,
                )
            raise

        logger.info(
            "Payment created",
            extra={"order_id": order.id, "payment_id": payment.id, "provider_id": provider_id},
        )
        return Response(
            {
                "payment_id": payment.id,
                "payment_url": payment.payment_url,
                "external_id": payment.external_id,
            },
            status=status.HTTP_201_CREATED,
        )


class PaymentWebhookView(APIView):
    """Обработать статус платежа и синхронизировать статус заказа."""

    permission_classes = [AllowAny]

    def post(self, request, provider_id):
        """Применить входящий webhook-событие к соответствующему платежу."""
        serializer = PaymentWebhookSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            payment = (
                Payment.objects.select_for_update()
                .select_related("order")
                .filter(provider_id=provider_id, external_id=data["external_id"])
                .first()
            )
            if not payment:
                return Response({"detail": "Payment not found."}, status=status.HTTP_404_NOT_FOUND)

            if payment.status in {PaymentStatus.SUCCEEDED, PaymentStatus.FAILED}:
                logger.info(
                    "Webhook already processed",
                    extra={"payment_id": payment.id, "provider_id": provider_id, "status": payment.status},
                )
                return Response({"ok": True, "already_processed": True}, status=status.HTTP_200_OK)

            incoming_status = data["status"]
            now = timezone.now()

            if incoming_status == PaymentStatus.SUCCEEDED:
                payment.status = PaymentStatus.SUCCEEDED
                payment.completed_at = now
                payment.save(update_fields=["status", "completed_at", "updated_at"])

                if payment.order.status != OrderStatus.PAID:
                    payment.order.status = OrderStatus.PAID
                    payment.order.paid_at = now
                    payment.order.save(update_fields=["status", "paid_at", "updated_at"])
            else:
                payment.status = PaymentStatus.FAILED
                payment.save(update_fields=["status", "updated_at"])

                if payment.order.status != OrderStatus.PAID:
                    payment.order.status = OrderStatus.PAYMENT_FAILED
                    payment.order.save(update_fields=["status", "updated_at"])

        logger.info(
            "Webhook processed",
            extra={"payment_id": payment.id, "provider_id": provider_id, "status": payment.status},
        )
        return Response({"ok": True}, status=status.HTTP_200_OK)
