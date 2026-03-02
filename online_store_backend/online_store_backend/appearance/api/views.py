"""API публичного и административного управления оформлением магазина."""

from django.db import transaction
from django.db.models import Q
from rest_framework import status
from rest_framework.permissions import AllowAny
from rest_framework.permissions import IsAdminUser
from rest_framework.response import Response
from rest_framework.views import APIView

from ..models import AppearanceBanner
from ..models import AppearancePreset
from ..models import PresetType
from ..models import ShopAppearanceSettings
from ..services import ensure_shop_appearance_initialized
from ..services import get_scope_settings
from ..services import publish_draft_to_live
from ..services import public_appearance_payload
from ..services import reset_draft_from_live
from ..services import serialize_settings
from .serializers import AppearanceBannerSerializer
from .serializers import AppearancePresetSerializer
from .serializers import DraftAppearanceSettingsSerializer


class ShopAppearancePublicView(APIView):
    """Публичный endpoint опубликованных настроек оформления витрины."""

    permission_classes = [AllowAny]

    def get(self, request):
        """Вернуть текущие live-настройки оформления для storefront."""
        payload = public_appearance_payload(request=request)
        return Response(payload, status=status.HTTP_200_OK)


class AdminAppearanceDraftView(APIView):
    """Чтение и обновление draft-настроек оформления."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Получить текущие черновые настройки оформления."""
        draft = get_scope_settings(is_published=False)
        return Response(serialize_settings(draft, request=request), status=status.HTTP_200_OK)

    def put(self, request):
        """Обновить черновые настройки оформления, включая загрузку/очистку логотипа."""
        draft = get_scope_settings(is_published=False)
        serializer = DraftAppearanceSettingsSerializer(data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)

        clear_logo = bool(serializer.validated_data.get("clear_logo"))
        changed_fields = []
        for field, value in serializer.validated_data.items():
            if field == "clear_logo":
                continue
            setattr(draft, field, value)
            changed_fields.append(field)

        if clear_logo and draft.logo:
            draft.logo = None
            if "logo" not in changed_fields:
                changed_fields.append("logo")

        if changed_fields:
            draft.save(update_fields=[*changed_fields, "updated_at"])

        refreshed = get_scope_settings(is_published=False)
        return Response(serialize_settings(refreshed, request=request), status=status.HTTP_200_OK)


class AdminAppearancePublishView(APIView):
    """Публикация draft-настроек в live-область."""

    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request):
        """Скопировать текущий draft в опубликованную область."""
        publish_draft_to_live()
        return Response({"ok": True}, status=status.HTTP_200_OK)


class AdminAppearanceResetView(APIView):
    """Сброс draft-настроек до состояния live-области."""

    permission_classes = [IsAdminUser]

    @transaction.atomic
    def post(self, request):
        """Перезаписать draft-область актуальными опубликованными настройками."""
        reset_draft_from_live()
        draft = get_scope_settings(is_published=False)
        return Response(
            {"ok": True, "draft": serialize_settings(draft, request=request)},
            status=status.HTTP_200_OK,
        )


class AdminAppearancePresetListCreateView(APIView):
    """CRUD-операции списка пресетов в черновой области."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Вернуть список draft-пресетов с опциональным фильтром по типу."""
        ensure_shop_appearance_initialized()
        preset_type = (request.query_params.get("type") or "").strip()
        queryset = AppearancePreset.objects.filter(is_published=False)
        if preset_type:
            if preset_type not in PresetType.values:
                return Response(
                    {"detail": "Invalid type. Allowed: catalog_card, product_page, product_card."},
                    status=status.HTTP_400_BAD_REQUEST,
                )
            queryset = queryset.filter(preset_type=preset_type)
        serializer = AppearancePresetSerializer(queryset.order_by("preset_type", "name", "id"), many=True)
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request):
        """Создать новый draft-пресет и при необходимости сделать его активным."""
        ensure_shop_appearance_initialized()
        serializer = AppearancePresetSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        preset = serializer.save(is_published=False)

        draft = get_scope_settings(is_published=False)
        changed_fields = []
        if preset.preset_type == PresetType.CATALOG_CARD and draft.active_catalog_preset_id is None:
            draft.active_catalog_preset = preset
            changed_fields.append("active_catalog_preset")
        if preset.preset_type == PresetType.PRODUCT_PAGE and draft.active_product_page_preset_id is None:
            draft.active_product_page_preset = preset
            changed_fields.append("active_product_page_preset")
        if preset.preset_type == PresetType.PRODUCT_CARD and draft.active_product_card_preset_id is None:
            draft.active_product_card_preset = preset
            changed_fields.append("active_product_card_preset")
        if changed_fields:
            draft.save(update_fields=[*changed_fields, "updated_at"])

        return Response(AppearancePresetSerializer(preset).data, status=status.HTTP_201_CREATED)


class AdminAppearancePresetDetailView(APIView):
    """Обновление и удаление конкретного draft-пресета."""

    permission_classes = [IsAdminUser]

    def put(self, request, preset_id):
        """Обновить свойства и конфигурацию выбранного пресета."""
        preset = AppearancePreset.objects.filter(id=preset_id, is_published=False).first()
        if not preset:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AppearancePresetSerializer(preset, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, preset_id):
        """Удалить пресет, если он не используется как активный."""
        preset = AppearancePreset.objects.filter(id=preset_id, is_published=False).first()
        if not preset:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        is_active = ShopAppearanceSettings.objects.filter(
            Q(active_catalog_preset_id=preset.id)
            | Q(active_product_page_preset_id=preset.id)
            | Q(active_product_card_preset_id=preset.id)
        ).exists()
        if is_active:
            return Response(
                {"detail": "Cannot delete an active preset. Switch active preset first."},
                status=status.HTTP_400_BAD_REQUEST,
            )

        preset.delete()
        ensure_shop_appearance_initialized()
        return Response(status=status.HTTP_204_NO_CONTENT)


class AdminAppearanceBannerListCreateView(APIView):
    """CRUD списка баннеров в draft-области оформления."""

    permission_classes = [IsAdminUser]

    def get(self, request):
        """Вернуть список черновых баннеров."""
        ensure_shop_appearance_initialized()
        banners = AppearanceBanner.objects.filter(is_published=False).order_by("sort_order", "id")
        serializer = AppearanceBannerSerializer(banners, many=True)
        return Response({"results": serializer.data}, status=status.HTTP_200_OK)

    def post(self, request):
        """Создать новый баннер в draft-области."""
        ensure_shop_appearance_initialized()
        serializer = AppearanceBannerSerializer(data=request.data)
        serializer.is_valid(raise_exception=True)
        banner = serializer.save(is_published=False)
        return Response(AppearanceBannerSerializer(banner).data, status=status.HTTP_201_CREATED)


class AdminAppearanceBannerDetailView(APIView):
    """Обновление и удаление конкретного draft-баннера."""

    permission_classes = [IsAdminUser]

    def put(self, request, banner_id):
        """Обновить параметры существующего баннера."""
        banner = AppearanceBanner.objects.filter(id=banner_id, is_published=False).first()
        if not banner:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        serializer = AppearanceBannerSerializer(banner, data=request.data, partial=True)
        serializer.is_valid(raise_exception=True)
        serializer.save()
        return Response(serializer.data, status=status.HTTP_200_OK)

    def delete(self, request, banner_id):
        """Удалить выбранный баннер."""
        banner = AppearanceBanner.objects.filter(id=banner_id, is_published=False).first()
        if not banner:
            return Response({"detail": "Not found."}, status=status.HTTP_404_NOT_FOUND)

        banner.delete()
        return Response(status=status.HTTP_204_NO_CONTENT)
