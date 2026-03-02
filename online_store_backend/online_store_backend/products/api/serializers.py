"""Сериализаторы публичного API каталога."""

from rest_framework import serializers


class ProductCategorySerializer(serializers.Serializer):
    """Вложенная категория в ответе карточки товара."""

    id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    slug = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    title = serializers.CharField(allow_null=True, allow_blank=True, required=False)


class CategorySerializer(serializers.Serializer):
    """Категория каталога в публичном API."""

    id = serializers.CharField()
    slug = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    title = serializers.CharField(allow_null=True, allow_blank=True, required=False)


class ProductSerializer(serializers.Serializer):
    """Публичное представление товара в каталоге."""

    id = serializers.CharField()
    slug = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    title = serializers.CharField()
    description = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    price = serializers.CharField()
    currency = serializers.CharField()
    image_url = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    thumbnail_url = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    gallery_urls = serializers.ListField(
        child=serializers.CharField(),
        required=False,
        allow_empty=True,
    )
    category = ProductCategorySerializer(allow_null=True, required=False)
    discount_percent = serializers.IntegerField(required=False)
    discounted_price = serializers.CharField(allow_null=True, allow_blank=True, required=False)
