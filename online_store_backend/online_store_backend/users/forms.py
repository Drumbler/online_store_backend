"""Формы пользователей для Django admin и allauth-регистрации."""

from allauth.account.forms import SignupForm
from allauth.socialaccount.forms import SignupForm as SocialSignupForm
from django.contrib.auth import forms as admin_forms
from django.utils.translation import gettext_lazy as _

from .models import User


class UserAdminChangeForm(admin_forms.UserChangeForm):
    """Форма редактирования пользователя в админке."""

    class Meta(admin_forms.UserChangeForm.Meta):  # type: ignore[name-defined]
        model = User


class UserAdminCreationForm(admin_forms.AdminUserCreationForm):
    """Форма создания пользователя в Django admin."""

    class Meta(admin_forms.UserCreationForm.Meta):  # type: ignore[name-defined]
        model = User
        error_messages = {
            "username": {"unique": _("This username has already been taken.")},
        }


class UserSignupForm(SignupForm):
    """Форма регистрации через стандартный allauth-поток."""


class UserSocialSignupForm(SocialSignupForm):
    """Форма регистрации для пользователей из социальных провайдеров."""
