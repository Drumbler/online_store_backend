from decimal import Decimal

from rest_framework import status
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import AllowAny
from rest_framework.response import Response
from rest_framework.viewsets import ViewSet

from .serializers import ProductSerializer

PRODUCTS = [
    {
        "id": "p-1001",
        "title": "Ceramic Mug",
        "description": "Glazed ceramic mug with matte finish.",
        "price": Decimal("590.00"),
        "currency": "RUB",
        "image_url": "https://example.com/images/mug.jpg",
        "category": {"id": "c-10", "title": "Kitchen"},
    },
    {
        "id": "p-1002",
        "title": "Notebook A5",
        "description": "Hardcover notebook with dotted pages.",
        "price": Decimal("320.00"),
        "currency": "RUB",
        "image_url": "https://example.com/images/notebook.jpg",
        "category": {"id": "c-20", "title": "Stationery"},
    },
    {
        "id": "p-1003",
        "title": "Wool Scarf",
        "description": "Soft wool scarf for cold seasons.",
        "price": Decimal("1490.00"),
        "currency": "RUB",
        "image_url": "https://example.com/images/scarf.jpg",
        "category": {"id": "c-30", "title": "Accessories"},
    },
    {
        "id": "p-1004",
        "title": "LED Desk Lamp",
        "description": "",
        "price": Decimal("2390.00"),
        "currency": "RUB",
        "image_url": None,
        "category": {"id": "c-40", "title": "Home"},
    },
    {
        "id": "p-1005",
        "title": "Wireless Mouse",
        "description": "Compact mouse with silent clicks.",
        "price": Decimal("990.00"),
        "currency": "RUB",
        "image_url": "https://example.com/images/mouse.jpg",
        "category": None,
    },
]


class ProductPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 100


class ProductViewSet(ViewSet):
    permission_classes = [AllowAny]
    serializer_class = ProductSerializer
    pagination_class = ProductPagination

    def list(self, request):
        paginator = self.pagination_class()
        page = paginator.paginate_queryset(PRODUCTS, request, view=self)
        serializer = self.serializer_class(page, many=True)
        return paginator.get_paginated_response(serializer.data)

    def retrieve(self, request, pk=None):
        product = next((item for item in PRODUCTS if item["id"] == pk), None)
        if not product:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)
        serializer = self.serializer_class(product)
        return Response(serializer.data, status=status.HTTP_200_OK)
