import logging
from urllib.parse import urlencode

from django.core.cache import cache
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from .serializers import CategorySerializer
from .serializers import ProductSerializer
from ..strapi_client import StrapiNotFoundError
from ..strapi_client import StrapiUnavailableError
from ..strapi_client import get_category
from ..strapi_client import get_product
from ..strapi_client import list_categories
from ..strapi_client import list_products

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


def _build_cache_key(prefix, query_params):
    items = []
    for key, values in query_params.lists():
        for value in values:
            items.append((key, value))
    items.sort()
    suffix = urlencode(items)
    return f"{prefix}:{suffix}" if suffix else prefix


class ProductViewSet(ViewSet):
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer

    def list(self, request):
        cache_key = _build_cache_key("products:list", request.query_params)
        cached = cache.get(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        page = _positive_int(request.query_params.get("page"), 1)
        page_size = _positive_int(request.query_params.get("page_size"), DEFAULT_PAGE_SIZE)
        if page_size > MAX_PAGE_SIZE:
            page_size = MAX_PAGE_SIZE
        try:
            results, pagination = list_products(page=page, page_size=page_size)
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while listing products.")
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        serializer = self.serializer_class(results, many=True)
        payload = {"results": serializer.data, "pagination": pagination}
        cache.set(cache_key, payload, timeout=60)
        return Response(payload, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        cache_key = f"products:detail:{pk}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        try:
            product = get_product(pk)
        except StrapiNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while retrieving product %s.", pk)
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        serializer = self.serializer_class(product)
        payload = serializer.data
        cache.set(cache_key, payload, timeout=300)
        return Response(payload, status=status.HTTP_200_OK)


class CategoryViewSet(ViewSet):
    permission_classes = [AllowAny]
    serializer_class = CategorySerializer

    def list(self, request):
        cache_key = _build_cache_key("categories:list", request.query_params)
        cached = cache.get(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        page = _positive_int(request.query_params.get("page"), 1)
        page_size = _positive_int(request.query_params.get("page_size"), DEFAULT_PAGE_SIZE)
        if page_size > MAX_PAGE_SIZE:
            page_size = MAX_PAGE_SIZE
        try:
            results, pagination = list_categories(page=page, page_size=page_size)
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while listing categories.")
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        serializer = self.serializer_class(results, many=True)
        payload = {"results": serializer.data, "pagination": pagination}
        cache.set(cache_key, payload, timeout=60)
        return Response(payload, status=status.HTTP_200_OK)

    def retrieve(self, request, pk=None):
        cache_key = f"categories:detail:{pk}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        try:
            category = get_category(pk)
        except StrapiNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while retrieving category %s.", pk)
            return Response(
                {"detail": "Catalog service unavailable"},
                status=status.HTTP_502_BAD_GATEWAY,
            )
        serializer = self.serializer_class(category)
        payload = serializer.data
        cache.set(cache_key, payload, timeout=300)
        return Response(payload, status=status.HTTP_200_OK)
