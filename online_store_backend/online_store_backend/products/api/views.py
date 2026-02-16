import logging
from urllib.parse import urlencode

from django.core.cache import cache
from rest_framework import status
from rest_framework.decorators import action
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from .serializers import CategorySerializer
from .serializers import ProductSerializer
from ..strapi_client import StrapiNotFoundError
from ..strapi_client import StrapiUnavailableError
from ..strapi_client import get_category
from ..strapi_client import get_product
from ..strapi_client import get_product_by_slug
from ..strapi_client import list_categories
from ..strapi_client import list_products

logger = logging.getLogger(__name__)

DEFAULT_PAGE_SIZE = 20
MAX_PAGE_SIZE = 100
MAX_PUBLIC_PAGE_SIZE = 50
ALLOWED_ORDERING = {"price", "-price", "title", "-title"}


def _positive_int(value, default):
    try:
        value = int(value)
    except (TypeError, ValueError):
        return default
    if value < 1:
        return default
    return value


def _parse_products_query_params(request):
    errors = []
    raw_page = request.query_params.get("page")
    raw_page_size = request.query_params.get("page_size")
    raw_ordering = request.query_params.get("ordering")
    raw_category = request.query_params.get("category")
    raw_search = request.query_params.get("search")

    page = 1
    if raw_page not in (None, ""):
        try:
            page = int(raw_page)
        except (TypeError, ValueError):
            errors.append("Invalid page. Must be an integer >= 1.")
        else:
            if page < 1:
                errors.append("Invalid page. Must be an integer >= 1.")

    page_size = DEFAULT_PAGE_SIZE
    if raw_page_size not in (None, ""):
        try:
            page_size = int(raw_page_size)
        except (TypeError, ValueError):
            errors.append("Invalid page_size. Must be an integer between 1 and 50.")
        else:
            if page_size < 1 or page_size > MAX_PUBLIC_PAGE_SIZE:
                errors.append("Invalid page_size. Must be an integer between 1 and 50.")

    ordering = raw_ordering if raw_ordering not in (None, "") else None
    if ordering and ordering not in ALLOWED_ORDERING:
        errors.append("Invalid ordering. Allowed: price,-price,title,-title")

    category = raw_category.strip() if isinstance(raw_category, str) else raw_category
    if category == "":
        category = None
    search = raw_search.strip() if isinstance(raw_search, str) else raw_search
    if search == "":
        search = None

    if errors:
        return None, errors[0]

    return {
        "page": page,
        "page_size": page_size,
        "ordering": ordering,
        "category": category,
        "search": search,
    }, None


def _build_products_strapi_params(validated):
    params = {
        "pagination[page]": validated["page"],
        "pagination[pageSize]": validated["page_size"],
        "populate[0]": "image",
        "populate[1]": "category",
    }
    if validated.get("category"):
        params["filters[category][slug][$eq]"] = validated["category"]
    if validated.get("search"):
        params["filters[title][$containsi]"] = validated["search"]
    ordering = validated.get("ordering")
    if ordering:
        if ordering == "price":
            params["sort"] = "price:asc"
        elif ordering == "-price":
            params["sort"] = "price:desc"
        elif ordering == "title":
            params["sort"] = "title:asc"
        elif ordering == "-title":
            params["sort"] = "title:desc"
    return params


def _products_cache_key(validated):
    parts = [
        f"page={validated['page']}",
        f"page_size={validated['page_size']}",
        f"ordering={validated.get('ordering') or ''}",
        f"category={validated.get('category') or ''}",
        f"search={validated.get('search') or ''}",
    ]
    return "products:list:" + "|".join(parts)


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
        validated, error = _parse_products_query_params(request)
        if error:
            return Response({"detail": error}, status=status.HTTP_400_BAD_REQUEST)
        cache_key = _products_cache_key(validated)
        cached = cache.get(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        try:
            params = _build_products_strapi_params(validated)
            results, pagination = list_products(
                page=validated["page"],
                page_size=validated["page_size"],
                params=params,
            )
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

    @action(detail=False, methods=["get"], url_path=r"by-slug/(?P<slug>[^/.]+)")
    def by_slug(self, request, slug=None):
        if not slug:
            return Response({"detail": "Slug is required."}, status=status.HTTP_400_BAD_REQUEST)
        cache_key = f"products:by-slug:{slug}"
        cached = cache.get(cache_key)
        if cached:
            return Response(cached, status=status.HTTP_200_OK)
        try:
            product = get_product_by_slug(slug)
        except StrapiNotFoundError:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        except StrapiUnavailableError:
            logger.exception("Strapi unavailable while retrieving product by slug %s.", slug)
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
