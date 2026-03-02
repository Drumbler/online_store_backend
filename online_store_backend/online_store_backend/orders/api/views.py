"""API заказов и отзывов: список заказов, lookup, отзывы и рейтинги товаров."""

from decimal import Decimal
from decimal import InvalidOperation

from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
from django.db.models import Avg
from django.db.models import Count
from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework.viewsets import ReadOnlyModelViewSet

from online_store_backend.cart.models import CartStatus
from online_store_backend.cart.utils import get_active_cart
from online_store_backend.products.strapi_client import StrapiNotFoundError
from online_store_backend.products.strapi_client import StrapiUnavailableError
from online_store_backend.products.strapi_client import get_product

from ..models import Order
from ..models import OrderItem
from ..models import Review
from ..models import OrderStatus
from ..pricing import clamp_discount_percent
from ..pricing import compute_discounted_unit_price
from ..pricing import compute_line_total
from .serializers import EligibleReviewProductSerializer
from .serializers import OrderLookupSerializer
from .serializers import OrderSerializer
from .serializers import ReviewCreateSerializer
from .serializers import ReviewSerializer

DEFAULT_REVIEWS_PAGE_SIZE = 10
MAX_REVIEWS_PAGE_SIZE = 50
ALLOWED_REVIEW_SORTS = {"created_desc", "created_asc", "rating_desc", "rating_asc"}


class OrderPagination(PageNumberPagination):
    """Пагинация списка заказов для личного кабинета."""

    page_size = 20


class OrderViewSet(ReadOnlyModelViewSet):
    """Чтение заказов текущего пользователя или всех заказов для админа."""

    serializer_class = OrderSerializer
    permission_classes = [IsAuthenticated]
    pagination_class = OrderPagination

    def get_queryset(self):
        """Ограничить выборку заказами текущего пользователя (или всеми для staff)."""
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
        """Сохраненный legacy-эндпоинт с подсказкой на новый двухшаговый checkout."""
        return Response(
            {"detail": "Use /api/checkout/preview/ and /api/checkout/confirm/ for checkout."},
            status=status.HTTP_400_BAD_REQUEST,
        )

    @action(
        detail=False,
        methods=["get"],
        url_path="lookup",
        permission_classes=[AllowAny],
        authentication_classes=[],
    )
    def lookup(self, request):
        """Публичный поиск заказа по номеру и секрету (для гостей)."""
        number = request.query_params.get("number")
        order_secret = request.query_params.get("order_secret")
        if not number:
            return Response({"detail": "Order number is required."}, status=status.HTTP_400_BAD_REQUEST)
        if not order_secret:
            return Response({"detail": "Order secret is required."}, status=status.HTTP_400_BAD_REQUEST)
        try:
            order_id = int(number)
        except (TypeError, ValueError):
            return Response({"detail": "Order number is invalid."}, status=status.HTTP_400_BAD_REQUEST)

        order = Order.objects.filter(id=order_id, order_secret=order_secret).prefetch_related("items").first()

        if not order:
            return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = OrderLookupSerializer(order)
        return Response(serializer.data, status=status.HTTP_200_OK)


def _positive_int(value, default):
    """Привести значение к положительному int или вернуть значение по умолчанию."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed < 1:
        return default
    return parsed


def _parse_product_ids_csv(value):
    """Разобрать CSV со списком product_id, удаляя пустые значения и дубликаты."""
    if value in (None, ""):
        return []
    product_ids = []
    seen = set()
    for raw in value.split(","):
        product_id = raw.strip()
        if not product_id or product_id in seen:
            continue
        seen.add(product_id)
        product_ids.append(product_id)
    return product_ids


def _review_summaries(product_ids):
    """Построить сводку рейтингов и количества отзывов по списку товаров."""
    summaries = {
        product_id: {"avg_rating": None, "reviews_count": 0}
        for product_id in product_ids
    }
    if not product_ids:
        return summaries

    rows = (
        Review.objects.filter(product_id__in=product_ids)
        .values("product_id")
        .annotate(avg_rating=Avg("rating"), reviews_count=Count("id"))
    )
    for row in rows:
        avg_rating = row["avg_rating"]
        summaries[row["product_id"]] = {
            "avg_rating": round(float(avg_rating), 1) if avg_rating is not None else None,
            "reviews_count": int(row["reviews_count"] or 0),
        }
    return summaries


class ProductReviewListView(APIView):
    """Публичный список отзывов по товару с фильтрацией и пагинацией."""

    permission_classes = [AllowAny]

    def get(self, request, product_id):
        """Вернуть отзывы товара с сортировкой и опциональным фильтром по рейтингу."""
        sort = request.query_params.get("sort", "created_desc")
        if sort not in ALLOWED_REVIEW_SORTS:
            return Response({"detail": "Invalid sort value."}, status=status.HTTP_400_BAD_REQUEST)

        rating_gte_param = request.query_params.get("rating_gte")
        rating_gte = None
        if rating_gte_param not in (None, ""):
            try:
                rating_gte = int(rating_gte_param)
            except (TypeError, ValueError):
                return Response({"detail": "rating_gte must be an integer between 1 and 5."}, status=status.HTTP_400_BAD_REQUEST)
            if rating_gte < 1 or rating_gte > 5:
                return Response({"detail": "rating_gte must be an integer between 1 and 5."}, status=status.HTTP_400_BAD_REQUEST)

        queryset = Review.objects.filter(product_id=product_id, is_published=True)
        if rating_gte is not None:
            queryset = queryset.filter(rating__gte=rating_gte)

        if sort == "created_desc":
            queryset = queryset.order_by("-created_at")
        elif sort == "created_asc":
            queryset = queryset.order_by("created_at")
        elif sort == "rating_desc":
            queryset = queryset.order_by("-rating", "-created_at")
        elif sort == "rating_asc":
            queryset = queryset.order_by("rating", "-created_at")

        total = queryset.count()
        limit_param = request.query_params.get("limit")
        if limit_param not in (None, ""):
            try:
                limit = int(limit_param)
            except (TypeError, ValueError):
                return Response({"detail": "limit must be an integer >= 1."}, status=status.HTTP_400_BAD_REQUEST)
            if limit < 1:
                return Response({"detail": "limit must be an integer >= 1."}, status=status.HTTP_400_BAD_REQUEST)
            reviews = list(queryset[:limit])
            page = 1
            page_size = limit
        else:
            page = _positive_int(request.query_params.get("page"), 1)
            page_size = _positive_int(request.query_params.get("page_size"), DEFAULT_REVIEWS_PAGE_SIZE)
            page_size = min(page_size, MAX_REVIEWS_PAGE_SIZE)
            offset = (page - 1) * page_size
            reviews = list(queryset[offset : offset + page_size])

        serializer = ReviewSerializer(reviews, many=True)
        return Response(
            {
                "results": serializer.data,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                },
            },
            status=status.HTTP_200_OK,
        )


class ReviewSummaryView(APIView):
    """Публичная сводка отзывов по группе товаров."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Вернуть агрегированную статистику рейтингов по `product_ids`."""
        product_ids = _parse_product_ids_csv(request.query_params.get("product_ids"))
        if not product_ids:
            return Response(
                {"detail": "product_ids query param is required."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        return Response(
            {"results": _review_summaries(product_ids)},
            status=status.HTTP_200_OK,
        )


class ProductRatingSummaryView(APIView):
    """Публичная сводка рейтинга по одному товару."""

    permission_classes = [AllowAny]

    def get(self, request, product_id):
        """Вернуть средний рейтинг и количество отзывов для конкретного товара."""
        summary = _review_summaries([product_id]).get(product_id, {"avg_rating": None, "reviews_count": 0})
        return Response(summary, status=status.HTTP_200_OK)


class EligibleReviewProductsView(APIView):
    """Список купленных товаров, по которым пользователь может оставить отзыв."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Вернуть кандидатов на отзыв для auth-пользователя или гостя по секрету заказа."""
        if request.user.is_authenticated:
            items_queryset = (
                OrderItem.objects.filter(order__user=request.user, review_left_at__isnull=True)
                .select_related("order")
                .order_by("-order__created_at", "-id")
            )
        else:
            number = request.query_params.get("order_number")
            order_secret = request.query_params.get("order_secret")
            if not number or not order_secret:
                return Response(
                    {"detail": "order_number and order_secret are required for guests."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            try:
                order_id = int(number)
            except (TypeError, ValueError):
                return Response({"detail": "order_number is invalid."}, status=status.HTTP_400_BAD_REQUEST)
            order = Order.objects.filter(id=order_id, order_secret=order_secret).first()
            if not order:
                return Response({"detail": "Order not found."}, status=status.HTTP_404_NOT_FOUND)
            items_queryset = OrderItem.objects.filter(order=order, review_left_at__isnull=True).select_related("order").order_by("-id")

        seen_products = set()
        payload = []
        for item in items_queryset:
            if item.product_id in seen_products:
                continue
            seen_products.add(item.product_id)
            title = item.product_title_snapshot
            image_url = item.image_url_snapshot
            try:
                product = get_product(item.product_id)
                title = product.get("title") or title
                image_url = product.get("image_url") or image_url
            except (StrapiNotFoundError, StrapiUnavailableError):
                pass
            payload.append(
                {
                    "product_id": item.product_id,
                    "title": title or "",
                    "image_url": image_url,
                    "review_token": item.review_token,
                }
            )

        serializer = EligibleReviewProductSerializer(payload, many=True)
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)


class ReviewCreateView(APIView):
    """Создание отзыва по одноразовому review-токену позиции заказа."""

    permission_classes = [AllowAny]

    def post(self, request):
        """Сохранить отзыв и пометить позицию заказа как уже оцененную."""
        serializer = ReviewCreateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        data = serializer.validated_data

        with transaction.atomic():
            order_item = (
                OrderItem.objects.select_for_update()
                .select_related("order")
                .filter(review_token=data["review_token"])
                .first()
            )
            if not order_item:
                return Response({"detail": "Invalid review token."}, status=status.HTTP_400_BAD_REQUEST)
            if order_item.review_left_at:
                return Response({"detail": "Review already left for this purchase item."}, status=status.HTTP_400_BAD_REQUEST)

            is_anonymous = bool(data.get("is_anonymous", False))
            author_user = request.user if request.user.is_authenticated else None
            if is_anonymous:
                author_display_name = "Anonymous"
            elif author_user:
                author_display_name = author_user.name or author_user.username
            else:
                author_display_name = "Guest"

            review = Review.objects.create(
                product_id=order_item.product_id,
                order=order_item.order,
                rating=data["rating"],
                pros=(data.get("pros") or ""),
                cons=(data.get("cons") or ""),
                comment=(data.get("comment") or ""),
                is_anonymous=is_anonymous,
                author_user=author_user,
                author_display_name=author_display_name,
            )
            order_item.review_left_at = timezone.now()
            order_item.save(update_fields=["review_left_at", "updated_at"])

        return Response(ReviewSerializer(review).data, status=status.HTTP_201_CREATED)
