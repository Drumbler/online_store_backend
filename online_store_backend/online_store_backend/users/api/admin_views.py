from django.contrib.auth import get_user_model
from django.db.models import Q
from rest_framework.mixins import ListModelMixin
from rest_framework.mixins import RetrieveModelMixin
from rest_framework.mixins import UpdateModelMixin
from rest_framework.pagination import PageNumberPagination
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.viewsets import GenericViewSet

from .admin_serializers import AdminUserSerializer

User = get_user_model()


class AdminUserPagination(PageNumberPagination):
    page_size = 20
    page_size_query_param = "page_size"
    max_page_size = 50

    def get_paginated_response(self, data):
        page_size = self.get_page_size(self.request) or len(data)
        return Response(
            {
                "results": data,
                "pagination": {
                    "page": self.page.number,
                    "page_size": page_size,
                    "total": self.page.paginator.count,
                },
            }
        )


class AdminUserViewSet(ListModelMixin, RetrieveModelMixin, UpdateModelMixin, GenericViewSet):
    serializer_class = AdminUserSerializer
    permission_classes = [IsAdminUser]
    pagination_class = AdminUserPagination
    queryset = User.objects.all()
    http_method_names = ["get", "patch", "head", "options"]

    def get_queryset(self):
        queryset = self.queryset
        params = self.request.query_params

        search = params.get("search")
        if search:
            queryset = queryset.filter(
                Q(username__icontains=search)
                | Q(email__icontains=search)
                | Q(name__icontains=search)
            )

        role = params.get("role")
        if role == "admin":
            queryset = queryset.filter(is_staff=True)
        elif role == "user":
            queryset = queryset.filter(is_staff=False)

        active = params.get("active")
        if active is not None:
            active_value = active.strip().lower()
            if active_value in {"true", "false"}:
                queryset = queryset.filter(is_active=(active_value == "true"))

        return queryset.order_by("id")
