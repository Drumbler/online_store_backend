from django.urls import path

from .account_views import AccountChangePasswordView
from .account_views import AccountEmailRequestVerificationView
from .account_views import AccountEmailSetView
from .account_views import AccountEmailVerifyView
from .account_views import AccountMeView

urlpatterns = [
    path("me/", AccountMeView.as_view(), name="account-me"),
    path("email/set/", AccountEmailSetView.as_view(), name="account-email-set"),
    path(
        "email/request-verification/",
        AccountEmailRequestVerificationView.as_view(),
        name="account-email-request-verification",
    ),
    path("email/verify/", AccountEmailVerifyView.as_view(), name="account-email-verify"),
    path("change-password/", AccountChangePasswordView.as_view(), name="account-change-password"),
]
