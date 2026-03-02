"""API авторизации и выдачи JWT-токенов."""

from django.contrib.auth import get_user_model
from rest_framework import serializers
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAuthenticated
from rest_framework.response import Response
from rest_framework.views import APIView
from rest_framework_simplejwt.serializers import TokenObtainPairSerializer
from rest_framework_simplejwt.tokens import RefreshToken
from rest_framework_simplejwt.views import TokenObtainPairView
from rest_framework_simplejwt.views import TokenRefreshView
from rest_framework_simplejwt.views import TokenVerifyView

from .auth_serializers import LoginSerializer
from .auth_serializers import RegisterSerializer
from .auth_serializers import UserMeSerializer
from .auth_serializers import UserPublicSerializer

User = get_user_model()


def _jwt_pair_for_user(user):
    """Сформировать пару JWT-токенов (access + refresh) для пользователя."""
    refresh = RefreshToken.for_user(user)
    return {"access": str(refresh.access_token), "refresh": str(refresh)}


class UsernameOrEmailTokenObtainPairSerializer(TokenObtainPairSerializer):
    """Получение JWT-пары с поддержкой входа по username или email."""

    username_or_email = serializers.CharField(write_only=True, required=False)

    def __init__(self, *args, **kwargs):
        """Разрешить вход без обязательного поля `username` в payload."""
        super().__init__(*args, **kwargs)
        # Поддерживаем либо username, либо username_or_email без обязательного username.
        self.fields[self.username_field].required = False

    def validate(self, attrs):
        """Преобразовать email в username и передать в стандартную валидацию SimpleJWT."""
        provided_username = (attrs.get(self.username_field, "") or "").strip()
        username_or_email = (attrs.pop("username_or_email", "") or "").strip()
        login_value = username_or_email or provided_username
        if not login_value:
            raise serializers.ValidationError({"username_or_email": ["This field is required."]})

        user = User.objects.filter(email__iexact=login_value).only(self.username_field).first()
        attrs[self.username_field] = getattr(user, self.username_field) if user else login_value
        return super().validate(attrs)


class JwtTokenCreateView(TokenObtainPairView):
    """Эндпоинт `POST /api/auth/jwt/create/`."""

    serializer_class = UsernameOrEmailTokenObtainPairSerializer
    permission_classes = [AllowAny]
    authentication_classes = []


class JwtTokenRefreshView(TokenRefreshView):
    """Эндпоинт `POST /api/auth/jwt/refresh/`."""

    permission_classes = [AllowAny]
    authentication_classes = []


class JwtTokenVerifyView(TokenVerifyView):
    """Эндпоинт `POST /api/auth/jwt/verify/`."""

    permission_classes = [AllowAny]
    authentication_classes = []


class RegisterView(APIView):
    """Регистрация пользователя и немедленная выдача JWT-пары."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """Создать пользователя по данным формы регистрации."""
        serializer = RegisterSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        user = serializer.save()
        return Response(
            {**_jwt_pair_for_user(user), "user": UserPublicSerializer(user).data},
            status=status.HTTP_201_CREATED,
        )


class LoginView(APIView):
    """Классический логин с возвратом JWT-пары и публичных данных пользователя."""

    permission_classes = [AllowAny]
    authentication_classes = []

    def post(self, request):
        """Аутентифицировать пользователя по username/email и паролю."""
        serializer = LoginSerializer(data=request.data, context={"request": request})
        serializer.is_valid(raise_exception=True)
        user = serializer.validated_data["user"]
        return Response({**_jwt_pair_for_user(user), "user": UserPublicSerializer(user).data})


class MeView(APIView):
    """Вернуть профиль текущего авторизованного пользователя."""

    permission_classes = [IsAuthenticated]

    def get(self, request):
        """Получить данные текущего пользователя."""
        return Response(UserMeSerializer(request.user).data)


class LogoutView(APIView):
    """Выход из аккаунта на уровне клиентской сессии."""

    permission_classes = [IsAuthenticated]

    def post(self, request):
        """Подтвердить logout; фактическая очистка JWT выполняется на клиенте."""
        return Response(status=status.HTTP_204_NO_CONTENT)
