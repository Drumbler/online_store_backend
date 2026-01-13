from django.urls import path
from rest_framework.routers import SimpleRouter

from .views import CartItemViewSet
from .views import CartView

app_name = "cart"

router = SimpleRouter()
router.register("items", CartItemViewSet, basename="cart-item")

urlpatterns = [
    path("", CartView.as_view(), name="cart-detail"),
    *router.urls,
]
