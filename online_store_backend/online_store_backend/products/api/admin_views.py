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
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while listing categories.")
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        serializer = self.serializer_class(results, many=True)
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
        }
        updates = serializer.validated_data
        if "price" in updates:
            payload["price"] = str(updates["price"])
        if "category" in updates:
            payload["category"] = None if updates["category"] == "" else updates["category"]
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
