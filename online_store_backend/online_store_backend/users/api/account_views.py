from django.conf import settings
from django.core import signing
from django.core.mail import send_mail
from rest_framework import status
from rest_framework.authentication import TokenAuthentication
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView

from .account_serializers import AccountMeSerializer
from .account_serializers import AccountNameUpdateSerializer
from .account_serializers import ChangePasswordSerializer
from .account_serializers import EmailSetSerializer
from .account_serializers import EmailVerifySerializer

EMAIL_VERIFY_SALT = "email-verify"
DEFAULT_EMAIL_VERIFY_MAX_AGE = 60 * 60 * 24


class AccountMeView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def get(self, request):
        return Response(AccountMeSerializer(request.user).data)

    def patch(self, request):
        serializer = AccountNameUpdateSerializer(instance=request.user, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(AccountMeSerializer(request.user).data)


class AccountEmailSetView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        serializer = EmailSetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        email = serializer.validated_data["email"]
        user = request.user
        user.email = email
        user.email_verified = False
        user.save(update_fields=["email", "email_verified"])
        return Response(AccountMeSerializer(user).data)


class AccountEmailRequestVerificationView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        user = request.user
        if not user.email:
            return Response({"detail": "Email is not set."}, status=status.HTTP_400_BAD_REQUEST)

        token = signing.dumps({"user_id": user.id, "email": user.email}, salt=EMAIL_VERIFY_SALT)
        frontend_url = getattr(settings, "FRONTEND_URL", "http://localhost:5173")
        verify_url = f"{frontend_url.rstrip('/')}/account/verify-email?token={token}"

        subject = "Verify your email"
        message = (
            "Please verify your email by clicking the link below:\n\n"
            f"{verify_url}\n\n"
            "If you did not request this, you can ignore this email."
        )
        send_mail(subject, message, settings.DEFAULT_FROM_EMAIL, [user.email], fail_silently=False)
        return Response(status=status.HTTP_204_NO_CONTENT)


class AccountEmailVerifyView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        serializer = EmailVerifySerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        token = serializer.validated_data["token"]
        max_age = getattr(settings, "ACCOUNT_EMAIL_VERIFICATION_TOKEN_MAX_AGE", DEFAULT_EMAIL_VERIFY_MAX_AGE)

        try:
            payload = signing.loads(token, salt=EMAIL_VERIFY_SALT, max_age=max_age)
        except signing.BadSignature:
            return Response({"detail": "Invalid or expired token."}, status=status.HTTP_400_BAD_REQUEST)

        user = request.user
        if payload.get("user_id") != user.id or payload.get("email") != user.email:
            return Response({"detail": "Token does not match current user."}, status=status.HTTP_400_BAD_REQUEST)

        user.email_verified = True
        user.save(update_fields=["email_verified"])
        return Response(AccountMeSerializer(user).data)


class AccountChangePasswordView(APIView):
    permission_classes = [IsAuthenticated]
    authentication_classes = [TokenAuthentication]

    def post(self, request):
        serializer = ChangePasswordSerializer(data=request.data, context={"user": request.user})
        serializer.is_valid(raise_exception=True)
        user = request.user
        current_password = serializer.validated_data["current_password"]
        if not user.check_password(current_password):
            return Response({"current_password": ["Current password is incorrect."]}, status=status.HTTP_400_BAD_REQUEST)

        user.set_password(serializer.validated_data["new_password"])
        user.save()
        return Response(status=status.HTTP_204_NO_CONTENT)
