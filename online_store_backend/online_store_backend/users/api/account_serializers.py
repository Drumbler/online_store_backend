from django.contrib.auth import get_user_model
from django.contrib.auth.password_validation import validate_password
from rest_framework import serializers

User = get_user_model()


class AccountMeSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["id", "username", "name", "email", "email_verified"]
        read_only_fields = ["id", "username", "email", "email_verified"]


class AccountNameUpdateSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = ["name"]


class EmailSetSerializer(serializers.Serializer):
    email = serializers.EmailField()

    def validate_email(self, value: str) -> str:
        email = value.strip()
        if not email:
            raise serializers.ValidationError("Email cannot be empty.")
        return email


class EmailVerifySerializer(serializers.Serializer):
    token = serializers.CharField()


class ChangePasswordSerializer(serializers.Serializer):
    current_password = serializers.CharField()
    new_password = serializers.CharField()
    new_password_confirm = serializers.CharField()

    def validate(self, attrs):
        if attrs["new_password"] != attrs["new_password_confirm"]:
            raise serializers.ValidationError({"new_password_confirm": "Passwords do not match."})
        validate_password(attrs["new_password"], self.context.get("user"))
        return attrs
