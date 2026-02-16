import json
import logging
from decimal import Decimal, InvalidOperation, ROUND_HALF_UP

from django.utils import timezone
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from .admin_serializers import CategoryAdminSerializer
from .admin_serializers import CategoryDiscountApplySerializer
from .admin_serializers import BulkUpdateSerializer
from .admin_serializers import CategoryUpsertSerializer
from .admin_serializers import ProductAdminSerializer
from .admin_serializers import ProductUpdateSerializer
from .admin_serializers import ProductUpsertSerializer
from ..strapi_client import StrapiNotFoundError
from ..strapi_client import StrapiRequestError
from ..strapi_client import StrapiUnavailableError
from ..strapi_client import create_category_admin
from ..strapi_client import create_product_admin
from ..strapi_client import delete_category_admin
from ..strapi_client import delete_product_admin
from ..strapi_client import get_category_admin
from ..strapi_client import get_product_admin
from ..strapi_client import list_categories_admin
from ..strapi_client import list_products_admin
from ..strapi_client import get_product_admin_raw
from ..strapi_client import update_category_admin
from ..strapi_client import update_product_admin_raw
from ..strapi_client import update_product_admin_flat

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
CATEGORY_PRODUCTS_PAGE_SIZE = 100


def _positive_int(value, default):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    if value < 1:
        return default
    return value


def _build_pagination(page, page_size):
    page = _positive_int(page, 1)
    page_size = _positive_int(page_size, DEFAULT_PAGE_SIZE)
    if page_size > MAX_PAGE_SIZE:
        page_size = MAX_PAGE_SIZE
    return page, page_size


def _published_at(publish):
    return timezone.now().isoformat() if publish else None


def _extract_category_document_id(category):
    if not category:
        return None
    if isinstance(category, dict) and "data" in category:
        category = category["data"]
    if not isinstance(category, dict):
        return None
    return category.get("documentId") or category.get("id")


def _normalize_price_value(value):
    if value is None:
        return None
    try:
        decimal_value = Decimal(str(value)).quantize(Decimal("0.01"))
    except (InvalidOperation, ValueError):
        logger.warning("Invalid price value from Strapi: %r", value)
        return None
    return format(decimal_value, "f")


def _trim_strapi_message(text):
    message = None
    if text is not None:
        try:
            payload = json.loads(text)
        except (TypeError, ValueError):
            payload = None
        if isinstance(payload, dict):
            error = payload.get("error")
            if isinstance(error, dict):
                message = error.get("message") or error.get("name")
            if not message:
                message = payload.get("message")
    message = message or (str(text).strip() if text is not None else "")
    if not message:
        message = "Catalog service error."
    if len(message) > 300:
        message = f"{message[:297]}..."
    return message


def _is_slug_conflict(response_text):
    if not response_text:
        return False
    try:
        payload = json.loads(response_text)
    except (TypeError, ValueError):
        payload = None
    haystacks = []
    if isinstance(payload, dict):
        haystacks.append(json.dumps(payload, ensure_ascii=False).lower())
    haystacks.append(str(response_text).lower())
    for text in haystacks:
        if "slug" in text and ("unique" in text or "already" in text or "taken" in text):
            return True
    return False


def _slug_conflict_response():
    return Response(
        {"slug": ["This slug is already in use."]},
        status=status.HTTP_400_BAD_REQUEST,
    )


def _category_products_params(category_id, page, page_size):
    return {
        "pagination[page]": page,
        "pagination[pageSize]": page_size,
        "populate": "category",
        "filters[category][documentId][$eq]": category_id,
    }


def _build_product_payload(attrs):
    payload = {
        "title": attrs.get("title"),
        "slug": attrs.get("slug"),
        "description": attrs.get("description"),
        "price": _normalize_price_value(attrs.get("price")),
        "currency": attrs.get("currency") or "RUB",
        "category": _extract_category_document_id(attrs.get("category")),
        "discount_percent": attrs.get("discount_percent") or 0,
    }
    return payload


def _get_category_discount_stats(category_id):
    page = 1
    total_in_category = 0
    discounts = set()
    while True:
        params = _category_products_params(category_id, page, CATEGORY_PRODUCTS_PAGE_SIZE)
        products, pagination = list_products_admin(
            page=page,
            page_size=CATEGORY_PRODUCTS_PAGE_SIZE,
            params=params,
        )
        for product in products:
            total_in_category += 1
            discount_value = product.get("discount_percent") or 0
            try:
                discount_value = int(discount_value)
            except (TypeError, ValueError):
                discount_value = 0
            discounts.add(max(0, min(100, discount_value)))
        total = pagination.get("total") if isinstance(pagination, dict) else None
        if not total or page * CATEGORY_PRODUCTS_PAGE_SIZE >= int(total):
            break
        page += 1

    if total_in_category == 0:
        return {
            "product_count": 0,
            "derived_discount_percent": None,
            "derived_discount_is_mixed": False,
        }
    if len(discounts) == 1:
        return {
            "product_count": total_in_category,
            "derived_discount_percent": next(iter(discounts)),
            "derived_discount_is_mixed": False,
        }
    return {
        "product_count": total_in_category,
        "derived_discount_percent": None,
        "derived_discount_is_mixed": True,
    }


class CategoryAdminViewSet(ViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = CategoryAdminSerializer

    def list(self, request):
        page, page_size = _build_pagination(
            request.query_params.get("page"),
            request.query_params.get("page_size"),
        )
        try:
            results, pagination = list_categories_admin(page=page, page_size=page_size)
            enriched = []
            for category in results:
                stats = _get_category_discount_stats(category["id"])
                enriched.append({**category, **stats})
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while listing categories.")
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        except StrapiRequestError as exc:
            return Response(
                {"detail": _trim_strapi_message(exc.response_text)},
                status=exc.status_code,
            )
        serializer = self.serializer_class(enriched, many=True)
        return Response({"results": serializer.data, "pagination": pagination})

    def retrieve(self, request, pk=None):
        try:
            category = get_category_admin(pk)
        except StrapiNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while retrieving category %s.", pk)
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        serializer = self.serializer_class(category)
        return Response(serializer.data)

    def create(self, request):
        serializer = CategoryUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = {**serializer.validated_data}
        try:
            category = create_category_admin(payload)
        except StrapiRequestError as exc:
            if _is_slug_conflict(exc.response_text):
                return _slug_conflict_response()
            return Response(
                {"detail": _trim_strapi_message(exc.response_text)},
                status=exc.status_code,
            )
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while creating category.")
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        response_serializer = self.serializer_class(category)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        serializer = CategoryUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        payload = {**serializer.validated_data}
        try:
            category = update_category_admin(pk, payload)
        except StrapiNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except StrapiRequestError as exc:
            if _is_slug_conflict(exc.response_text):
                return _slug_conflict_response()
            return Response(
                {"detail": _trim_strapi_message(exc.response_text)},
                status=exc.status_code,
            )
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while updating category %s.", pk)
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        response_serializer = self.serializer_class(category)
        return Response(response_serializer.data)

    def destroy(self, request, pk=None):
        try:
            delete_category_admin(pk)
        except StrapiNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while deleting category %s.", pk)
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=True, methods=["post"], url_path="apply-discount")
    def apply_discount(self, request, pk=None):
        serializer = CategoryDiscountApplySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        requested_discount = serializer.validated_data["discount_percent"]
        page = 1
        updated_count = 0
        skipped_count = 0
        total_in_category = 0

        while True:
            params = _category_products_params(pk, page, CATEGORY_PRODUCTS_PAGE_SIZE)
            try:
                products, pagination = list_products_admin(
                    page=page,
                    page_size=CATEGORY_PRODUCTS_PAGE_SIZE,
                    params=params,
                )
            except StrapiUnavailableError:
                logger.exception(
                    "Strapi unavailable while applying category discount for %s.", pk
                )
                return Response(
                    {"detail": "Catalog service unavailable"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            for product in products:
                total_in_category += 1
                product_discount = product.get("discount_percent") or 0
                try:
                    product_discount = int(product_discount)
                except (TypeError, ValueError):
                    product_discount = 0
                product_discount = max(0, min(100, product_discount))
                if product_discount >= requested_discount:
                    skipped_count += 1
                    continue
                product_id = product.get("id")
                try:
                    attrs = get_product_admin_raw(product_id)
                    payload = _build_product_payload(attrs)
                    payload["discount_percent"] = requested_discount
                    update_product_admin_raw(product_id, payload)
                    updated_count += 1
                except StrapiNotFoundError:
                    skipped_count += 1
                except StrapiRequestError as exc:
                    return Response(
                        {"detail": _trim_strapi_message(exc.response_text)},
                        status=exc.status_code,
                    )
                except StrapiUnavailableError:
                    logger.exception(
                        "Strapi unavailable while applying discount to product %s.", product_id
                    )
                    return Response(
                        {"detail": "Catalog service unavailable"},
                        status=status.HTTP_502_BAD_GATEWAY,
                    )
            total = pagination.get("total") if isinstance(pagination, dict) else None
            if not total or page * CATEGORY_PRODUCTS_PAGE_SIZE >= int(total):
                break
            page += 1

        return Response(
            {
                "category_id": pk,
                "requested_discount": requested_discount,
                "updated_count": updated_count,
                "skipped_count": skipped_count,
                "total_in_category": total_in_category,
            }
        )

    @action(detail=True, methods=["post"], url_path="remove-discount")
    def remove_discount(self, request, pk=None):
        page = 1
        updated_count = 0
        skipped_count = 0
        total_in_category = 0

        while True:
            params = _category_products_params(pk, page, CATEGORY_PRODUCTS_PAGE_SIZE)
            try:
                products, pagination = list_products_admin(
                    page=page,
                    page_size=CATEGORY_PRODUCTS_PAGE_SIZE,
                    params=params,
                )
            except StrapiUnavailableError:
                logger.exception(
                    "Strapi unavailable while removing category discount for %s.", pk
                )
                return Response(
                    {"detail": "Catalog service unavailable"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            for product in products:
                total_in_category += 1
                product_id = product.get("id")
                product_discount = product.get("discount_percent") or 0
                try:
                    product_discount = int(product_discount)
                except (TypeError, ValueError):
                    product_discount = 0
                product_discount = max(0, min(100, product_discount))
                if product_discount == 0:
                    skipped_count += 1
                    continue
                try:
                    attrs = get_product_admin_raw(product_id)
                    payload = _build_product_payload(attrs)
                    payload["discount_percent"] = 0
                    update_product_admin_raw(product_id, payload)
                    updated_count += 1
                except StrapiNotFoundError:
                    skipped_count += 1
                except StrapiRequestError as exc:
                    return Response(
                        {"detail": _trim_strapi_message(exc.response_text)},
                        status=exc.status_code,
                    )
                except StrapiUnavailableError:
                    logger.exception(
                        "Strapi unavailable while removing discount from product %s.", product_id
                    )
                    return Response(
                        {"detail": "Catalog service unavailable"},
                        status=status.HTTP_502_BAD_GATEWAY,
                    )
            total = pagination.get("total") if isinstance(pagination, dict) else None
            if not total or page * CATEGORY_PRODUCTS_PAGE_SIZE >= int(total):
                break
            page += 1

        return Response(
            {
                "category_id": pk,
                "updated_count": updated_count,
                "skipped_count": skipped_count,
                "total_in_category": total_in_category,
            }
        )


class ProductAdminViewSet(ViewSet):
    permission_classes = [IsAdminUser]
    serializer_class = ProductAdminSerializer

    def list(self, request):
        page, page_size = _build_pagination(
            request.query_params.get("page"),
            request.query_params.get("page_size"),
        )
        try:
            results, pagination = list_products_admin(page=page, page_size=page_size)
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while listing products.")
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        serializer = self.serializer_class(results, many=True)
        return Response({"results": serializer.data, "pagination": pagination})

    def retrieve(self, request, pk=None):
        try:
            product = get_product_admin(pk)
        except StrapiNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while retrieving product %s.", pk)
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        serializer = self.serializer_class(product)
        return Response(serializer.data)

    def create(self, request):
        serializer = ProductUpsertSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        publish = serializer.validated_data.pop("publish", True)
        payload = {**serializer.validated_data, "publishedAt": _published_at(publish)}
        if "price" in payload:
            payload["price"] = str(payload["price"])
        if payload.get("category") == "":
            payload["category"] = None
        try:
            product = create_product_admin(payload)
        except StrapiRequestError as exc:
            if _is_slug_conflict(exc.response_text):
                return _slug_conflict_response()
            return Response(
                {"detail": _trim_strapi_message(exc.response_text)},
                status=exc.status_code,
            )
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while creating product.")
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        response_serializer = self.serializer_class(product)
        return Response(response_serializer.data, status=status.HTTP_201_CREATED)

    def update(self, request, pk=None):
        serializer = ProductUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        try:
            current = get_product_admin_raw(pk)
        except StrapiNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except StrapiRequestError as exc:
            if _is_slug_conflict(exc.response_text):
                return _slug_conflict_response()
            return Response(
                {"detail": _trim_strapi_message(exc.response_text)},
                status=exc.status_code,
            )
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while retrieving product %s.", pk)
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        payload = {
            "title": current.get("title"),
            "slug": current.get("slug"),
            "description": current.get("description"),
            "price": _normalize_price_value(current.get("price")),
            "currency": current.get("currency"),
            "category": _extract_category_document_id(current.get("category")),
            "discount_percent": current.get("discount_percent"),
        }
        updates = serializer.validated_data
        if "price" in updates:
            payload["price"] = str(updates["price"])
        if "category" in updates:
            payload["category"] = None if updates["category"] == "" else updates["category"]
        if "discount_percent" in updates:
            payload["discount_percent"] = updates["discount_percent"]
        for key in ("title", "slug", "description", "currency"):
            if key in updates:
                payload[key] = updates[key]
        try:
            product = update_product_admin_flat(pk, payload)
        except StrapiNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except StrapiRequestError as exc:
            return Response(
                {"detail": _trim_strapi_message(exc.response_text)},
                status=exc.status_code,
            )
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while updating product %s.", pk)
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        response_serializer = self.serializer_class(product)
        return Response(response_serializer.data)

    def destroy(self, request, pk=None):
        try:
            delete_product_admin(pk)
        except StrapiNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while deleting product %s.", pk)
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        return Response(status=status.HTTP_204_NO_CONTENT)

    @action(detail=False, methods=["post"], url_path="bulk-update")
    def bulk_update(self, request):
        serializer = BulkUpdateSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        product_ids = serializer.validated_data["product_ids"]
        operation = serializer.validated_data["operation"]
        operation_type = operation.get("type")
        if operation_type not in {
            "set_category",
            "discount_percent",
            "increase_price_fixed",
            "decrease_price_fixed",
        }:
            return Response(
                {"detail": "Unsupported operation type."},
                status=status.HTTP_400_BAD_REQUEST,
            )
        category_id = operation.get("category_id")
        if category_id == "":
            category_id = None
        value = operation.get("value")
        updated = 0
        failed = []
        for product_id in product_ids:
            try:
                attrs = get_product_admin_raw(product_id)
            except StrapiNotFoundError:
                failed.append({"id": product_id, "status": 404, "detail": "Not found."})
                continue
            except StrapiRequestError as exc:
                failed.append(
                    {
                        "id": product_id,
                        "status": exc.status_code,
                        "detail": exc.response_text,
                    }
                )
                continue
            except StrapiUnavailableError:
                logger.exception("Strapi unavailable while fetching product %s.", product_id)
                return Response(
                    {"detail": "Catalog service unavailable"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            price_value = attrs.get("price")
            if price_value is None:
                failed.append(
                    {"id": product_id, "status": 422, "detail": "Missing price on product."}
                )
                continue
            try:
                current_price = Decimal(str(price_value))
            except (InvalidOperation, ValueError):
                failed.append(
                    {"id": product_id, "status": 422, "detail": "Invalid price on product."}
                )
                continue
            if operation_type == "discount_percent":
                current_price = (current_price * (Decimal("1") - (value / Decimal("100")))).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
            elif operation_type == "increase_price_fixed":
                current_price = (current_price + value).quantize(
                    Decimal("0.01"),
                    rounding=ROUND_HALF_UP,
                )
            elif operation_type == "decrease_price_fixed":
                current_price = max(
                    (current_price - value).quantize(Decimal("0.01"), rounding=ROUND_HALF_UP),
                    Decimal("0.00"),
                )
            payload = {
                "title": attrs.get("title"),
                "slug": attrs.get("slug"),
                "description": attrs.get("description"),
                "price": str(current_price),
                "currency": attrs.get("currency"),
                "category": category_id
                if operation_type == "set_category"
                else _extract_category_document_id(attrs.get("category")),
            }
            try:
                update_product_admin_raw(product_id, payload)
            except StrapiNotFoundError:
                failed.append({"id": product_id, "status": 404, "detail": "Not found."})
            except StrapiRequestError as exc:
                failed.append(
                    {
                        "id": product_id,
                        "status": exc.status_code,
                        "detail": exc.response_text,
                    }
                )
            except StrapiUnavailableError:
                logger.exception("Strapi unavailable while updating product %s.", product_id)
                return Response(
                    {"detail": "Catalog service unavailable"},
                    status=status.HTTP_502_BAD_GATEWAY,
                )
            else:
                updated += 1
        return Response({"updated": updated, "failed": failed})
