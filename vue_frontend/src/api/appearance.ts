/** API-контракты и методы для управления внешним видом магазина. */
import { adminApiClient } from "./adminClient";
import { apiClient } from "./public";

export type AppearanceBlockType =
  | "title"
  | "price"
  | "rating"
  | "reviews_count"
  | "buy_button"
  | "short_description";

export type AppearancePresetType = "catalog_card" | "product_page" | "product_card";

export type AppearanceLayoutMode = "media_left" | "media_top" | "compact";

export type AppearancePhotoMode = "thumbnails_right" | "thumbnails_bottom" | "hover_carousel";

export type AppearancePresetBlock = {
  type: AppearanceBlockType;
  visible: boolean;
  order: number;
};

export type AppearancePresetConfig = {
  layout_mode: AppearanceLayoutMode;
  photo_mode: AppearancePhotoMode;
  blocks: AppearancePresetBlock[];
};

export type AppearancePreset = {
  id: number;
  preset_type: AppearancePresetType;
  name: string;
  config: AppearancePresetConfig;
  created_at?: string;
  updated_at?: string;
};

export type AppearanceBannerPlacement = "below_header" | "in_grid";

export type AppearanceBanner = {
  id: number;
  image_url: string;
  link_url: string;
  placement: AppearanceBannerPlacement;
  after_row: number | null;
  is_enabled: boolean;
  sort_order: number;
  created_at?: string;
  updated_at?: string;
};

export type ShopAppearancePayload = {
  theme_mode: "light" | "dark";
  primary_color: string;
  logo_url: string | null;
  grid_columns: number;
  card_height: number;
  spacing_level: number;
  presets: {
    catalog_card: AppearancePreset | null;
    product_page: AppearancePreset | null;
    product_card: AppearancePreset | null;
  };
  banners: AppearanceBanner[];
};

export type DraftAppearancePayload = {
  id: number;
  theme_mode: "light" | "dark";
  primary_color: string;
  logo_url: string | null;
  grid_columns: number;
  card_height: number;
  spacing_level: number;
  active_catalog_preset_id: number | null;
  active_product_page_preset_id: number | null;
  active_product_card_preset_id: number | null;
};

type DraftAppearanceUpdatePayload =
  | FormData
  | Partial<
      DraftAppearancePayload & {
        logo: File | null;
        clear_logo: boolean;
      }
    >;

/** Публичные настройки оформления для storefront. */
export const getShopAppearance = () => apiClient.get<ShopAppearancePayload>("/shop/appearance/");

/** Черновик настроек оформления (admin). */
export const getAppearanceDraft = () => adminApiClient.get<DraftAppearancePayload>("/admin/appearance/draft/");

/** Обновление черновика оформления (JSON или multipart/form-data). */
export const updateAppearanceDraft = (payload: DraftAppearanceUpdatePayload) =>
  adminApiClient.put<DraftAppearancePayload>("/admin/appearance/draft/", payload, {
    headers: payload instanceof FormData ? { "Content-Type": "multipart/form-data" } : undefined
  });

/** Публикует текущий draft как публичную тему магазина. */
export const publishAppearanceDraft = () => adminApiClient.post<{ ok: boolean }>("/admin/appearance/publish/");

/** Сбрасывает draft к последнему опубликованному состоянию. */
export const resetAppearanceDraft = () =>
  adminApiClient.post<{ ok: boolean; draft: DraftAppearancePayload }>("/admin/appearance/reset/");

/** Список пресетов по типу (`catalog_card`, `product_page`, `product_card`). */
export const listAppearancePresets = (type?: AppearancePresetType) =>
  adminApiClient.get<{ results: AppearancePreset[] }>("/admin/appearance/presets/", {
    params: type ? { type } : undefined
  });

/** Создает новый пресет оформления. */
export const createAppearancePreset = (payload: {
  preset_type: AppearancePresetType;
  name: string;
  config: AppearancePresetConfig;
}) => adminApiClient.post<AppearancePreset>("/admin/appearance/presets/", payload);

/** Обновляет существующий пресет оформления. */
export const updateAppearancePreset = (
  presetId: number,
  payload: Partial<{ name: string; config: AppearancePresetConfig }>
) => adminApiClient.put<AppearancePreset>(`/admin/appearance/presets/${presetId}/`, payload);

/** Удаляет пресет оформления. */
export const deleteAppearancePreset = (presetId: number) =>
  adminApiClient.delete(`/admin/appearance/presets/${presetId}/`);

/** Возвращает список баннеров оформления. */
export const listAppearanceBanners = () =>
  adminApiClient.get<{ results: AppearanceBanner[] }>("/admin/appearance/banners/");

/** Создает баннер оформления. */
export const createAppearanceBanner = (payload: Omit<AppearanceBanner, "id">) =>
  adminApiClient.post<AppearanceBanner>("/admin/appearance/banners/", payload);

/** Обновляет баннер оформления. */
export const updateAppearanceBanner = (
  bannerId: number,
  payload: Partial<Omit<AppearanceBanner, "id">>
) => adminApiClient.put<AppearanceBanner>(`/admin/appearance/banners/${bannerId}/`, payload);

/** Удаляет баннер оформления. */
export const deleteAppearanceBanner = (bannerId: number) =>
  adminApiClient.delete(`/admin/appearance/banners/${bannerId}/`);
