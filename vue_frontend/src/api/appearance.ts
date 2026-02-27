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

export const getShopAppearance = () => apiClient.get<ShopAppearancePayload>("/shop/appearance/");

export const getAppearanceDraft = () => adminApiClient.get<DraftAppearancePayload>("/admin/appearance/draft/");

export const updateAppearanceDraft = (payload: DraftAppearanceUpdatePayload) =>
  adminApiClient.put<DraftAppearancePayload>("/admin/appearance/draft/", payload, {
    headers: payload instanceof FormData ? { "Content-Type": "multipart/form-data" } : undefined
  });

export const publishAppearanceDraft = () => adminApiClient.post<{ ok: boolean }>("/admin/appearance/publish/");

export const resetAppearanceDraft = () =>
  adminApiClient.post<{ ok: boolean; draft: DraftAppearancePayload }>("/admin/appearance/reset/");

export const listAppearancePresets = (type?: AppearancePresetType) =>
  adminApiClient.get<{ results: AppearancePreset[] }>("/admin/appearance/presets/", {
    params: type ? { type } : undefined
  });

export const createAppearancePreset = (payload: {
  preset_type: AppearancePresetType;
  name: string;
  config: AppearancePresetConfig;
}) => adminApiClient.post<AppearancePreset>("/admin/appearance/presets/", payload);

export const updateAppearancePreset = (
  presetId: number,
  payload: Partial<{ name: string; config: AppearancePresetConfig }>
) => adminApiClient.put<AppearancePreset>(`/admin/appearance/presets/${presetId}/`, payload);

export const deleteAppearancePreset = (presetId: number) =>
  adminApiClient.delete(`/admin/appearance/presets/${presetId}/`);

export const listAppearanceBanners = () =>
  adminApiClient.get<{ results: AppearanceBanner[] }>("/admin/appearance/banners/");

export const createAppearanceBanner = (payload: Omit<AppearanceBanner, "id">) =>
  adminApiClient.post<AppearanceBanner>("/admin/appearance/banners/", payload);

export const updateAppearanceBanner = (
  bannerId: number,
  payload: Partial<Omit<AppearanceBanner, "id">>
) => adminApiClient.put<AppearanceBanner>(`/admin/appearance/banners/${bannerId}/`, payload);

export const deleteAppearanceBanner = (bannerId: number) =>
  adminApiClient.delete(`/admin/appearance/banners/${bannerId}/`);
