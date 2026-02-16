from django.contrib.auth import authenticate
from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class UserPublicSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "email", "name"]
        read_only_fields = fields


class UserMeSerializer(serializers.ModelSerializer):
    is_admin = serializers.SerializerMethodField()

    class Meta:
        model = User
        fields = ["id", "username", "email", "name", "is_staff", "is_superuser", "is_admin"]
        read_only_fields = fields

    def get_is_admin(self, user):
        return bool(user.is_staff or user.is_superuser)


class RegisterSerializer(serializers.Serializer):
    username = serializers.CharField()
    email = serializers.EmailField(required=False, allow_blank=True)
    password = serializers.CharField(write_only=True)

    def validate_username(self, value):
        if User.objects.filter(username=value).exists():
            raise serializers.ValidationError("Username already exists.")
        return value

    def create(self, validated_data):
        email = validated_data.get("email") or ""
        return User.objects.create_user(
            username=validated_data["username"],
            email=email,
            password=validated_data["password"],
        )


class LoginSerializer(serializers.Serializer):
    username_or_email = serializers.CharField()
    password = serializers.CharField(write_only=True)

    def validate(self, attrs):
        username_or_email = attrs.get("username_or_email", "").strip()
        password = attrs.get("password")
        user = User.objects.filter(email__iexact=username_or_email).first()
        username = user.username if user else username_or_email
        user = authenticate(self.context.get("request"), username=username, password=password)
        if not user:
            raise serializers.ValidationError("Invalid credentials.")
        if not user.is_active:
            raise serializers.ValidationError("User account is disabled.")
        attrs["user"] = user
        return attrs
