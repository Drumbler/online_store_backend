"""URL-маршруты auth API (JWT и профиль)."""

from django.urls import path

from .auth_views import JwtTokenCreateView
from .auth_views import JwtTokenRefreshView
from .auth_views import JwtTokenVerifyView
from .auth_views import LoginView
from .auth_views import LogoutView
from .auth_views import MeView
from .auth_views import RegisterView

urlpatterns = [
    path("jwt/create/", JwtTokenCreateView.as_view(), name="auth-jwt-create"),
    path("jwt/refresh/", JwtTokenRefreshView.as_view(), name="auth-jwt-refresh"),
    path("jwt/verify/", JwtTokenVerifyView.as_view(), name="auth-jwt-verify"),
    path("register/", RegisterView.as_view(), name="auth-register"),
    path("login/", LoginView.as_view(), name="auth-login"),
    path("me/", MeView.as_view(), name="auth-me"),
    path("logout/", LogoutView.as_view(), name="auth-logout"),
]
