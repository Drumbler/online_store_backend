"""Конфигурация Django-приложения корзины."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class CartConfig(AppConfig):
    """Регистрация приложения cart в Django."""

    name = "online_store_backend.cart"
    verbose_name = _("Cart")
