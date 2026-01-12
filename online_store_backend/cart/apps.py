from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CartConfig(AppConfig):
    name = "online_store_backend.cart"
    verbose_name = _("Cart")
