from rest_framework import serializers


class ProductCategorySerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()


class ProductSerializer(serializers.Serializer):
    id = serializers.CharField()
    title = serializers.CharField()
    description = serializers.CharField(allow_blank=True)
    price = serializers.DecimalField(max_digits=10, decimal_places=2)
    currency = serializers.CharField()
    image_url = serializers.URLField(allow_null=True)
    category = ProductCategorySerializer(allow_null=True)
