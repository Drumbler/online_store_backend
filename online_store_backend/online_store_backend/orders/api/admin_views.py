"""Админские API для модерации отзывов и формирования отчетов по продажам."""

import logging
from collections import defaultdict
from datetime import timedelta
from decimal import Decimal
from io import BytesIO

from django.http import HttpResponse
from django.db.models import CharField
from django.db.models import Count
from django.db.models import DecimalField
from django.db.models import ExpressionWrapper
from django.db.models import F
from django.db.models import IntegerField
from django.db.models import OuterRef
from django.db.models import Q
from django.db.models import Subquery
from django.db.models import Sum
from django.db.models import Value
from django.db.models.functions import Cast
from django.db.models.functions import Coalesce
from django.db.models.functions import ExtractMonth
from django.db.models.functions import ExtractYear
from django.utils import timezone
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from online_store_backend.products.strapi_client import StrapiNotFoundError
from online_store_backend.products.strapi_client import StrapiUnavailableError
from online_store_backend.products.strapi_client import get_product

from ..models import OrderStatus
from ..models import OrderItem
from ..models import ProductViewEvent
from ..models import Review

logger = logging.getLogger(__name__)

DEFAULT_REVIEWS_PAGE_SIZE = 20
MAX_REVIEWS_PAGE_SIZE = 100
ALLOWED_REVIEW_SORTS = {"created_desc", "created_asc", "rating_desc", "rating_asc"}


class ReviewModerationUpdateSerializer(serializers.Serializer):
    """Payload для изменения публикации одного отзыва."""

    is_published = serializers.BooleanField()


class ReviewModerationBulkSerializer(serializers.Serializer):
    """Payload для массовой модерации отзывов."""

    ids = serializers.ListField(
        child=serializers.IntegerField(min_value=1),
        allow_empty=False,
    )
    is_published = serializers.BooleanField()


def _positive_int(value, default):
    """Преобразует значение в положительное целое или возвращает default."""
    try:
        parsed = int(value)
    except (TypeError, ValueError):
        return default
    if parsed < 1:
        return default
    return parsed


def _normalize_list_params(query_params):
    """Нормализует параметры пагинации списка отзывов."""
    page = _positive_int(query_params.get("page"), 1)
    page_size = _positive_int(query_params.get("page_size"), DEFAULT_REVIEWS_PAGE_SIZE)
    if page_size > MAX_REVIEWS_PAGE_SIZE:
        page_size = MAX_REVIEWS_PAGE_SIZE
    return page, page_size


def _base_queryset():
    """Строит базовый queryset отзывов с аннотациями snapshot-данных товара."""
    order_item_for_review = OrderItem.objects.filter(
        order_id=OuterRef("order_id"),
        product_id=OuterRef("product_id"),
    ).order_by("id")
    return (
        Review.objects.select_related("order")
        .annotate(
            order_number_text=Cast("order_id", output_field=CharField()),
            product_title_snapshot=Subquery(order_item_for_review.values("product_title_snapshot")[:1]),
            product_image_url_snapshot=Subquery(order_item_for_review.values("image_url_snapshot")[:1]),
        )
    )


def _apply_filters(queryset, query_params):
    """Применяет фильтры рейтинга, публикации и текстового поиска."""
    rating_gte = query_params.get("rating_gte")
    if rating_gte not in (None, ""):
        try:
            parsed = int(rating_gte)
        except (TypeError, ValueError):
            raise serializers.ValidationError({"rating_gte": "rating_gte must be an integer between 1 and 5."})
        if parsed < 1 or parsed > 5:
            raise serializers.ValidationError({"rating_gte": "rating_gte must be an integer between 1 and 5."})
        queryset = queryset.filter(rating__gte=parsed)

    is_published = query_params.get("is_published", "all")
    if is_published not in {"all", "true", "false"}:
        raise serializers.ValidationError({"is_published": "is_published must be one of: all, true, false."})
    if is_published == "true":
        queryset = queryset.filter(is_published=True)
    elif is_published == "false":
        queryset = queryset.filter(is_published=False)

    q = (query_params.get("q") or "").strip()
    if q:
        queryset = queryset.filter(
            Q(comment__icontains=q)
            | Q(pros__icontains=q)
            | Q(cons__icontains=q)
            | Q(author_display_name__icontains=q)
            | Q(order_number_text__icontains=q)
            | Q(product_title_snapshot__icontains=q)
        )
    return queryset


def _apply_sort(queryset, sort):
    """Применяет сортировку по дате или рейтингу для списка отзывов."""
    if sort not in ALLOWED_REVIEW_SORTS:
        raise serializers.ValidationError({"sort": "Invalid sort value."})
    if sort == "created_desc":
        return queryset.order_by("-created_at", "-id")
    if sort == "created_asc":
        return queryset.order_by("created_at", "id")
    if sort == "rating_desc":
        return queryset.order_by("-rating", "-created_at", "-id")
    return queryset.order_by("rating", "-created_at", "-id")


def _load_products(product_ids):
    """Загружает из каталога метаданные товаров для списка отзывов."""
    products = {}
    catalog_unavailable = False
    for product_id in product_ids:
        if catalog_unavailable:
            break
        try:
            product = get_product(product_id)
            products[product_id] = {
                "title": product.get("title"),
                "image_url": product.get("image_url"),
            }
        except StrapiNotFoundError:
            continue
        except StrapiUnavailableError:
            catalog_unavailable = True
            logger.warning("Catalog service unavailable while enriching admin reviews.")
    return products


def _serialize_review(review, products):
    """Собирает JSON-представление отзыва для ответа admin API."""
    product = products.get(review.product_id) or {}
    product_title = product.get("title") or None
    product_image_url = product.get("image_url") or None
    return {
        "id": review.id,
        "product_id": review.product_id,
        "product_title": product_title,
        "product_image_url": product_image_url,
        "rating": review.rating,
        "pros": review.pros or None,
        "cons": review.cons or None,
        "comment": review.comment or None,
        "author_display_name": review.author_display_name,
        "is_anonymous": review.is_anonymous,
        "order_number": str(review.order_id) if review.order_id else None,
        "created_at": review.created_at,
        "is_published": review.is_published,
    }


class AdminReviewListView(APIView):
    """Возвращает список отзывов для модерации в админке."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Отдает пагинированный список отзывов с фильтрами."""
        try:
            queryset = _apply_filters(_base_queryset(), request.query_params)
            queryset = _apply_sort(queryset, request.query_params.get("sort", "created_desc"))
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)

        page, page_size = _normalize_list_params(request.query_params)
        total = queryset.count()
        offset = (page - 1) * page_size
        reviews = list(queryset[offset : offset + page_size])
        product_ids = sorted({review.product_id for review in reviews})
        products = _load_products(product_ids)
        payload = [_serialize_review(review, products) for review in reviews]
        return Response(
            {
                "results": payload,
                "pagination": {
                    "page": page,
                    "page_size": page_size,
                    "total": total,
                },
            },
            status=status.HTTP_200_OK,
        )


class AdminReviewModerationView(APIView):
    """Изменяет флаг публикации одного отзыва."""

    permission_classes = [IsAdminUser]

    def patch(self, request, review_id):
        """Применяет модерацию к выбранному отзыву."""
        serializer = ReviewModerationUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        new_value = serializer.validated_data["is_published"]

        review = _base_queryset().filter(id=review_id).first()
        if not review:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        if review.is_published != new_value:
            review.is_published = new_value
            review.moderated_at = timezone.now()
            review.moderated_by = request.user
            review.save(update_fields=["is_published", "moderated_at", "moderated_by"])
            review = _base_queryset().get(id=review_id)

        products = _load_products([review.product_id])
        return Response(_serialize_review(review, products), status=status.HTTP_200_OK)


class AdminReviewModerationBulkView(APIView):
    """Массово изменяет флаг публикации отзывов."""

    permission_classes = [IsAdminUser]

    def post(self, request):
        """Обновляет список отзывов по переданным id."""
        serializer = ReviewModerationBulkSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        ids = serializer.validated_data["ids"]
        new_value = serializer.validated_data["is_published"]

        updated = Review.objects.filter(id__in=ids).exclude(is_published=new_value).update(
            is_published=new_value,
            moderated_at=timezone.now(),
            moderated_by=request.user,
        )
        return Response({"updated": updated}, status=status.HTTP_200_OK)


class MonthlyReportQuerySerializer(serializers.Serializer):
    """Параметры периода для месячного отчета."""

    year = serializers.IntegerField(required=False, min_value=2000, max_value=2100)
    month = serializers.IntegerField(required=False, min_value=1, max_value=12)


class YearlyReportQuerySerializer(serializers.Serializer):
    """Параметры периода для годового отчета."""

    year = serializers.IntegerField(required=False, min_value=2000, max_value=2100)


def _current_local_time():
    """Возвращает текущее локальное время с учетом таймзоны проекта."""
    return timezone.localtime(timezone.now())


def _month_period(year: int, month: int, now_local):
    """Вычисляет границы месяца для отчета."""
    period_from = now_local.replace(year=year, month=month, day=1, hour=0, minute=0, second=0, microsecond=0)
    if year == now_local.year and month == now_local.month:
        return period_from, now_local

    next_year = year + 1 if month == 12 else year
    next_month = 1 if month == 12 else month + 1
    next_month_start = now_local.replace(
        year=next_year,
        month=next_month,
        day=1,
        hour=0,
        minute=0,
        second=0,
        microsecond=0,
    )
    return period_from, next_month_start - timedelta(microseconds=1)


def _year_period(year: int, now_local):
    """Вычисляет границы года для отчета."""
    period_from = now_local.replace(year=year, month=1, day=1, hour=0, minute=0, second=0, microsecond=0)
    period_to = now_local.replace(year=year, month=12, day=31, hour=23, minute=59, second=59, microsecond=999999)
    return period_from, period_to


def _resolve_month_period(query_params):
    """Валидирует query-параметры и возвращает границы месяца."""
    now_local = _current_local_time()
    serializer = MonthlyReportQuerySerializer(data=query_params)
    serializer.is_valid(raise_exception=True)
    year = serializer.validated_data.get("year", now_local.year)
    month = serializer.validated_data.get("month", now_local.month)
    period_from, period_to = _month_period(year, month, now_local)
    return year, month, period_from, period_to


def _resolve_year_period(query_params):
    """Валидирует query-параметры и возвращает границы года."""
    now_local = _current_local_time()
    serializer = YearlyReportQuerySerializer(data=query_params)
    serializer.is_valid(raise_exception=True)
    year = serializer.validated_data.get("year", now_local.year)
    period_from, period_to = _year_period(year, now_local)
    return year, period_from, period_to


def _format_revenue(value):
    """Нормализует выручку к строке с двумя знаками после запятой."""
    decimal_value = value if isinstance(value, Decimal) else Decimal(str(value or "0.00"))
    return format(decimal_value.quantize(Decimal("0.01")), "f")


def _build_report_payload(period_from, period_to):
    """Строит сводный отчет по просмотрам, продажам и выручке товаров."""
    views_rows = (
        ProductViewEvent.objects.filter(viewed_at__gte=period_from, viewed_at__lte=period_to)
        .values("product_id")
        .annotate(views=Count("id"))
    )
    views_by_product = {str(row["product_id"]): int(row["views"] or 0) for row in views_rows}

    sales_queryset = (
        OrderItem.objects.filter(order__status=OrderStatus.PAID)
        .annotate(sale_moment=Coalesce("order__paid_at", "order__created_at"))
        .filter(sale_moment__gte=period_from, sale_moment__lte=period_to)
    )
    line_total_expr = Coalesce(
        F("line_total"),
        ExpressionWrapper(
            F("unit_price") * F("quantity"),
            output_field=DecimalField(max_digits=12, decimal_places=2),
        ),
    )
    sales_rows = sales_queryset.values("product_id").annotate(
        units_sold=Coalesce(Sum("quantity"), Value(0), output_field=IntegerField()),
        revenue=Coalesce(
            Sum(line_total_expr),
            Value(Decimal("0.00")),
            output_field=DecimalField(max_digits=14, decimal_places=2),
        ),
    )
    sales_by_product = {}
    for row in sales_rows:
        product_id = str(row["product_id"])
        sales_by_product[product_id] = {
            "units_sold": int(row["units_sold"] or 0),
            "revenue": row["revenue"] if isinstance(row["revenue"], Decimal) else Decimal(str(row["revenue"] or "0.00")),
        }

    titles_by_product = {}
    latest_title_rows = (
        sales_queryset.exclude(product_title_snapshot__isnull=True)
        .exclude(product_title_snapshot="")
        .order_by("-sale_moment", "-id")
        .values("product_id", "product_title_snapshot")
    )
    for row in latest_title_rows:
        product_id = str(row["product_id"])
        if product_id in titles_by_product:
            continue
        titles_by_product[product_id] = str(row["product_title_snapshot"] or "").strip()

    product_ids = set(views_by_product.keys()) | set(sales_by_product.keys())

    for product_id in sorted(product_ids):
        if titles_by_product.get(product_id):
            continue
        try:
            product = get_product(product_id)
            title = str(product.get("title") or "").strip()
        except StrapiNotFoundError:
            title = ""
        except StrapiUnavailableError:
            logger.warning("Catalog service unavailable while enriching report titles.")
            title = ""
        titles_by_product[product_id] = title

    results = []
    total_views = 0
    total_units_sold = 0
    total_revenue = Decimal("0.00")

    for product_id in sorted(product_ids, key=lambda value: (titles_by_product.get(value) or value).lower()):
        sales_data = sales_by_product.get(product_id, {"units_sold": 0, "revenue": Decimal("0.00")})
        units_sold = int(sales_data["units_sold"])
        revenue = sales_data["revenue"] if isinstance(sales_data["revenue"], Decimal) else Decimal(str(sales_data["revenue"] or "0.00"))
        views = int(views_by_product.get(product_id, 0))
        title = titles_by_product.get(product_id) or product_id

        total_views += views
        total_units_sold += units_sold
        total_revenue += revenue

        results.append(
            {
                "product_id": product_id,
                "title": title,
                "views": views,
                "units_sold": units_sold,
                "revenue": _format_revenue(revenue),
            }
        )

    return {
        "period": {
            "from": period_from.date().isoformat(),
            "to": period_to.date().isoformat(),
        },
        "totals": {
            "views": total_views,
            "units_sold": total_units_sold,
            "revenue": _format_revenue(total_revenue),
        },
        "results": results,
    }


def _available_month_periods():
    """Возвращает доступные месяцы/годы, где есть просмотры или продажи."""
    views_rows = ProductViewEvent.objects.annotate(
        year=ExtractYear("viewed_at"),
        month=ExtractMonth("viewed_at"),
    ).values_list("year", "month").distinct()

    sales_rows = (
        OrderItem.objects.filter(order__status=OrderStatus.PAID)
        .annotate(sale_moment=Coalesce("order__paid_at", "order__created_at"))
        .annotate(year=ExtractYear("sale_moment"), month=ExtractMonth("sale_moment"))
        .values_list("year", "month")
        .distinct()
    )

    months_by_year = defaultdict(set)
    for year, month in list(views_rows) + list(sales_rows):
        if year is None or month is None:
            continue
        months_by_year[int(year)].add(int(month))

    years = sorted(months_by_year.keys(), reverse=True)
    return years, {str(year): sorted(months_by_year[year]) for year in years}


def _xlsx_response(payload, filename: str):
    """Формирует и возвращает XLSX-файл с данными отчета."""
    try:
        from openpyxl import Workbook
    except ImportError:
        logger.exception("openpyxl is not installed.")
        return Response({"detail": "Excel export dependency is not installed."}, status=status.HTTP_500_INTERNAL_SERVER_ERROR)

    workbook = Workbook()
    worksheet = workbook.active
    worksheet.title = "Report"
    worksheet.append(
        [
            "ИТОГО",
            payload["totals"]["views"],
            payload["totals"]["units_sold"],
            payload["totals"]["revenue"],
        ]
    )
    worksheet.append(["Название товара", "Просмотры", "Продано", "Выручка"])

    for row in payload["results"]:
        worksheet.append([row["title"], row["views"], row["units_sold"], row["revenue"]])

    stream = BytesIO()
    workbook.save(stream)
    stream.seek(0)

    response = HttpResponse(
        stream.getvalue(),
        content_type="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet",
    )
    response["Content-Disposition"] = f'attachment; filename="{filename}"'
    return response


class AdminReportPeriodsView(APIView):
    """Возвращает список доступных периодов для отчетов."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Отдает годы и месяцы, где есть данные для аналитики."""
        years, months_by_year = _available_month_periods()
        return Response({"years": years, "months_by_year": months_by_year}, status=status.HTTP_200_OK)


class AdminMonthlyReportView(APIView):
    """Возвращает JSON-отчет за месяц."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Строит месячный отчет по выбранному периоду."""
        try:
            _, _, period_from, period_to = _resolve_month_period(request.query_params)
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        payload = _build_report_payload(period_from, period_to)
        return Response(payload, status=status.HTTP_200_OK)


class AdminMonthlyReportXlsxView(APIView):
    """Возвращает XLSX-отчет за месяц."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Генерирует месячный отчет в формате Excel."""
        try:
            year, month, period_from, period_to = _resolve_month_period(request.query_params)
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        payload = _build_report_payload(period_from, period_to)
        return _xlsx_response(payload, filename=f"monthly_report_{year}_{month:02}.xlsx")


class AdminYearlyReportView(APIView):
    """Возвращает JSON-отчет за год."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Строит годовой отчет по выбранному периоду."""
        try:
            _, period_from, period_to = _resolve_year_period(request.query_params)
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        payload = _build_report_payload(period_from, period_to)
        return Response(payload, status=status.HTTP_200_OK)


class AdminYearlyReportXlsxView(APIView):
    """Возвращает XLSX-отчет за год."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Генерирует годовой отчет в формате Excel."""
        try:
            year, period_from, period_to = _resolve_year_period(request.query_params)
        except serializers.ValidationError as exc:
            return Response(exc.detail, status=status.HTTP_400_BAD_REQUEST)
        payload = _build_report_payload(period_from, period_to)
        return _xlsx_response(payload, filename=f"yearly_report_{year}.xlsx")
