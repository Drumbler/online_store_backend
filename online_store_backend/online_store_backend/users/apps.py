"""Конфигурация Django-приложения пользователей."""

from django.apps import AppConfig
from django.utils.translation import gettext_lazy as _


class UsersConfig(AppConfig):
    """Регистрация пользовательского приложения в Django."""

    name = "online_store_backend.users"
    verbose_name = _("Users")

    def ready(self):
        """Точка расширения для startup-инициализации при необходимости."""
