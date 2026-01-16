from django.conf import settings
from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from online_store_backend.orders.api.views import OrderViewSet
from online_store_backend.products.api.admin_views import CategoryAdminViewSet
from online_store_backend.products.api.admin_views import ProductAdminViewSet
from online_store_backend.products.api.views import CategoryViewSet
from online_store_backend.products.api.views import ProductViewSet
from online_store_backend.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()
admin_router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("orders", OrderViewSet, basename="orders")
router.register("categories", CategoryViewSet, basename="categories")
router.register("products", ProductViewSet, basename="products")
admin_router.register("categories", CategoryAdminViewSet, basename="admin-categories")
admin_router.register("products", ProductAdminViewSet, basename="admin-products")


app_name = "api"
urlpatterns = [
    path("auth/", include("online_store_backend.users.api.auth_urls")),
    path("cart/", include("online_store_backend.cart.urls")),
    path("admin/catalog/", include(admin_router.urls)),
    *router.urls,
]
