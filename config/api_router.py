from django.conf import settings
from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from online_store_backend.orders.api.views import OrderViewSet
from online_store_backend.products.api.views import ProductViewSet
from online_store_backend.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("orders", OrderViewSet, basename="orders")
router.register("products", ProductViewSet, basename="products")


app_name = "api"
urlpatterns = [
    path("cart/", include("online_store_backend.cart.urls")),
    *router.urls,
]
