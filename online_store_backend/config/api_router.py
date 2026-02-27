from django.conf import settings
from django.urls import include
from django.urls import path
from rest_framework.routers import DefaultRouter
from rest_framework.routers import SimpleRouter

from online_store_backend.appearance.api.views import AdminAppearanceBannerDetailView
from online_store_backend.appearance.api.views import AdminAppearanceBannerListCreateView
from online_store_backend.appearance.api.views import AdminAppearanceDraftView
from online_store_backend.appearance.api.views import AdminAppearancePresetDetailView
from online_store_backend.appearance.api.views import AdminAppearancePresetListCreateView
from online_store_backend.appearance.api.views import AdminAppearancePublishView
from online_store_backend.appearance.api.views import AdminAppearanceResetView
from online_store_backend.appearance.api.views import ShopAppearancePublicView
from online_store_backend.integrations.api.views import AdminIntegrationConfigView
from online_store_backend.integrations.api.views import AdminIntegrationsProvidersView
from online_store_backend.integrations.api.views import AdminIntegrationTestConnectionView
from online_store_backend.orders.api.admin_views import AdminReviewListView
from online_store_backend.orders.api.admin_views import AdminMonthlyReportView
from online_store_backend.orders.api.admin_views import AdminMonthlyReportXlsxView
from online_store_backend.orders.api.admin_views import AdminReportPeriodsView
from online_store_backend.orders.api.admin_views import AdminReviewModerationBulkView
from online_store_backend.orders.api.admin_views import AdminReviewModerationView
from online_store_backend.orders.api.admin_views import AdminYearlyReportView
from online_store_backend.orders.api.admin_views import AdminYearlyReportXlsxView
from online_store_backend.orders.api.payment_views import CheckoutPaymentMethodsView
from online_store_backend.orders.api.payment_views import PaymentCreateView
from online_store_backend.orders.api.payment_views import PaymentWebhookView
from online_store_backend.orders.api.checkout_views import CheckoutConfirmView
from online_store_backend.orders.api.checkout_views import CheckoutPreviewView
from online_store_backend.orders.api.checkout_views import CheckoutShippingMethodsView
from online_store_backend.orders.api.checkout_views import ShippingPickupPointsView
from online_store_backend.orders.api.checkout_views import ShippingQuoteView
from online_store_backend.orders.api.views import OrderViewSet
from online_store_backend.orders.api.views import ProductReviewListView
from online_store_backend.orders.api.views import EligibleReviewProductsView
from online_store_backend.orders.api.views import ProductRatingSummaryView
from online_store_backend.orders.api.views import ReviewCreateView
from online_store_backend.orders.api.views import ReviewSummaryView
from online_store_backend.products.api.admin_views import CategoryAdminViewSet
from online_store_backend.products.api.admin_views import ProductAdminViewSet
from online_store_backend.products.api.views import CategoryViewSet
from online_store_backend.products.api.views import ProductViewSet
from online_store_backend.users.api.admin_views import AdminUserViewSet
from online_store_backend.users.api.views import UserViewSet

router = DefaultRouter() if settings.DEBUG else SimpleRouter()
admin_catalog_router = DefaultRouter() if settings.DEBUG else SimpleRouter()
admin_user_router = DefaultRouter() if settings.DEBUG else SimpleRouter()

router.register("users", UserViewSet)
router.register("orders", OrderViewSet, basename="orders")
router.register("categories", CategoryViewSet, basename="categories")
router.register("products", ProductViewSet, basename="products")
admin_catalog_router.register("categories", CategoryAdminViewSet, basename="admin-categories")
admin_catalog_router.register("products", ProductAdminViewSet, basename="admin-products")
admin_user_router.register("users", AdminUserViewSet, basename="admin-users")


app_name = "api"
urlpatterns = [
    path("auth/", include("online_store_backend.users.api.auth_urls")),
    path("account/", include("online_store_backend.users.api.account_urls")),
    path("cart/", include("online_store_backend.cart.urls")),
    path("checkout/preview/", CheckoutPreviewView.as_view(), name="checkout-preview"),
    path("checkout/confirm/", CheckoutConfirmView.as_view(), name="checkout-confirm"),
    path("checkout/payment-methods/", CheckoutPaymentMethodsView.as_view(), name="checkout-payment-methods"),
    path("checkout/shipping-methods/", CheckoutShippingMethodsView.as_view(), name="checkout-shipping-methods"),
    path("shipping/<str:provider_id>/pickup-points/", ShippingPickupPointsView.as_view(), name="shipping-pickup-points"),
    path("shipping/<str:provider_id>/quote/", ShippingQuoteView.as_view(), name="shipping-quote"),
    path("shop/appearance/", ShopAppearancePublicView.as_view(), name="shop-appearance-public"),
    path("payments/", PaymentCreateView.as_view(), name="payments-create"),
    path("payments/webhook/<str:provider_id>/", PaymentWebhookView.as_view(), name="payments-webhook"),
    path("products/<str:product_id>/reviews/", ProductReviewListView.as_view(), name="product-reviews"),
    path("products/<str:product_id>/rating-summary/", ProductRatingSummaryView.as_view(), name="product-rating-summary"),
    path("reviews/eligible/", EligibleReviewProductsView.as_view(), name="reviews-eligible"),
    path("reviews/summary/", ReviewSummaryView.as_view(), name="reviews-summary"),
    path("reviews/", ReviewCreateView.as_view(), name="reviews-create"),
    path("admin/reviews/", AdminReviewListView.as_view(), name="admin-reviews-list"),
    path("admin/reviews/bulk/", AdminReviewModerationBulkView.as_view(), name="admin-reviews-bulk"),
    path("admin/reviews/<int:review_id>/", AdminReviewModerationView.as_view(), name="admin-reviews-update"),
    path("admin/reports/periods/", AdminReportPeriodsView.as_view(), name="admin-reports-periods"),
    path("admin/reports/monthly/", AdminMonthlyReportView.as_view(), name="admin-reports-monthly"),
    path("admin/reports/monthly.xlsx", AdminMonthlyReportXlsxView.as_view(), name="admin-reports-monthly-xlsx"),
    path("admin/reports/yearly/", AdminYearlyReportView.as_view(), name="admin-reports-yearly"),
    path("admin/reports/yearly.xlsx", AdminYearlyReportXlsxView.as_view(), name="admin-reports-yearly-xlsx"),
    path("admin/appearance/draft/", AdminAppearanceDraftView.as_view(), name="admin-appearance-draft"),
    path("admin/appearance/publish/", AdminAppearancePublishView.as_view(), name="admin-appearance-publish"),
    path("admin/appearance/reset/", AdminAppearanceResetView.as_view(), name="admin-appearance-reset"),
    path("admin/appearance/presets/", AdminAppearancePresetListCreateView.as_view(), name="admin-appearance-presets"),
    path("admin/appearance/presets/<int:preset_id>/", AdminAppearancePresetDetailView.as_view(), name="admin-appearance-presets-detail"),
    path("admin/appearance/banners/", AdminAppearanceBannerListCreateView.as_view(), name="admin-appearance-banners"),
    path("admin/appearance/banners/<int:banner_id>/", AdminAppearanceBannerDetailView.as_view(), name="admin-appearance-banners-detail"),
    path("admin/integrations/providers/", AdminIntegrationsProvidersView.as_view(), name="admin-integrations-providers"),
    path(
        "admin/integrations/configs/<str:kind>/<str:provider_id>/",
        AdminIntegrationConfigView.as_view(),
        name="admin-integration-config",
    ),
    path(
        "admin/integrations/configs/<str:kind>/<str:provider_id>/test/",
        AdminIntegrationTestConnectionView.as_view(),
        name="admin-integration-test",
    ),
    path("admin/catalog/", include(admin_catalog_router.urls)),
    path("admin/", include(admin_user_router.urls)),
    *router.urls,
]
