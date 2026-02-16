from rest_framework import serializers


class ProductCategorySerializer(serializers.Serializer):
    id = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    slug = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    title = serializers.CharField(allow_null=True, allow_blank=True, required=False)


class CategorySerializer(serializers.Serializer):
    id = serializers.CharField()
    slug = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    title = serializers.CharField(allow_null=True, allow_blank=True, required=False)


class ProductSerializer(serializers.Serializer):
    id = serializers.CharField()
    slug = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    title = serializers.CharField()
    description = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    price = serializers.CharField()
    currency = serializers.CharField()
    image_url = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    thumbnail_url = serializers.CharField(allow_null=True, allow_blank=True, required=False)
    category = ProductCategorySerializer(allow_null=True, required=False)
    discount_percent = serializers.IntegerField(required=False)
    discounted_price = serializers.CharField(allow_null=True, allow_blank=True, required=False)
