from django.contrib.auth import get_user_model
from rest_framework import serializers

User = get_user_model()


class AdminUserSerializer(serializers.ModelSerializer):
    class Meta:
        model = User
        fields = [
            "id",
            "username",
            "email",
            "name",
            "is_staff",
            "is_superuser",
            "is_active",
            "date_joined",
            "last_login",
        ]
        read_only_fields = [
            "id",
            "username",
            "email",
            "is_superuser",
            "date_joined",
            "last_login",
        ]

    def validate(self, attrs):
        if "is_superuser" in self.initial_data:
            raise serializers.ValidationError(
                {"is_superuser": "Updating is_superuser is not allowed."}
            )

        instance = getattr(self, "instance", None)
        if instance and instance.is_superuser:
            errors = {}
            if "is_staff" in attrs:
                errors["is_staff"] = "Cannot modify staff access for a superuser."
            if "is_active" in attrs:
                errors["is_active"] = "Cannot change active status for a superuser."
            if errors:
                raise serializers.ValidationError(errors)

        request = self.context.get("request")
        if instance and request and instance.pk == request.user.pk:
            if "is_staff" in attrs and attrs["is_staff"] is False:
                raise serializers.ValidationError(
                    {"is_staff": "You cannot remove your own staff access."}
                )
            if "is_active" in attrs and attrs["is_active"] is False:
                raise serializers.ValidationError(
                    {"is_active": "You cannot deactivate your own account."}
                )

        return attrs
