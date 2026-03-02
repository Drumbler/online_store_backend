"""Базовые сериализаторы users API."""

from rest_framework import serializers

from online_store_backend.users.models import User


class UserSerializer(serializers.ModelSerializer[User]):
    """Сериализатор пользователя для типового DRF viewset."""

    class Meta:
        model = User
        fields = ["username", "name", "url"]

        extra_kwargs = {
            "url": {"view_name": "api:user-detail", "lookup_field": "username"},
        }
