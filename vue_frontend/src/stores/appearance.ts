/** Pinia-store для публичных настроек темы/пресетов и баннеров витрины. */
import { defineStore } from "pinia";
import { computed, ref } from "vue";

import type { ShopAppearancePayload } from "../api/appearance";
import { getShopAppearance } from "../api/appearance";
import { buildThemeTokens, defaultPresetConfig, normalizePresetConfig } from "../utils/appearance";

const defaultAppearance = (): ShopAppearancePayload => ({
  theme_mode: "light",
  primary_color: "#ff6b00",
  logo_url: null,
  grid_columns: 4,
  card_height: 320,
  spacing_level: 2,
  presets: {
    catalog_card: {
      id: 0,
      preset_type: "catalog_card",
      name: "Catalog stock",
      config: defaultPresetConfig("catalog_card")
    },
    product_page: {
      id: 0,
      preset_type: "product_page",
      name: "Product page stock",
      config: defaultPresetConfig("product_page")
    },
    product_card: {
      id: 0,
      preset_type: "product_card",
      name: "Product card stock",
      config: defaultPresetConfig("product_card")
    }
  },
  banners: []
});

export const useAppearanceStore = defineStore("appearance", () => {
  const payload = ref<ShopAppearancePayload>(defaultAppearance());
  const loading = ref(false);
  const loaded = ref(false);
  const error = ref<string | null>(null);

  const loadPublishedAppearance = async (force = false) => {
    /** Загружает опубликованные настройки оформления магазина. */
    if (loading.value) {
      return;
    }
    if (loaded.value && !force) {
      return;
    }

    loading.value = true;
    error.value = null;
    try {
      const response = await getShopAppearance();
      const defaults = defaultAppearance();
      const incoming = response.data || defaults;
      payload.value = {
        ...defaults,
        ...incoming,
        presets: {
          ...defaults.presets,
          ...(incoming.presets || {})
        },
        banners: incoming.banners || []
      };
      loaded.value = true;
    } catch {
      error.value = "Failed to load storefront appearance.";
      if (!loaded.value) {
        payload.value = defaultAppearance();
      }
    } finally {
      loading.value = false;
    }
  };

  const themeTokens = computed(() => buildThemeTokens(payload.value.theme_mode, payload.value.primary_color));

  const storefrontCssVars = computed<Record<string, string>>(() => ({
    // Дублируем legacy `--store-*` и новые токены для совместимости компонентов.
    "--primary": themeTokens.value.primary,
    "--primary-contrast": themeTokens.value.primaryContrast,
    "--primary-soft": themeTokens.value.primarySoft,
    "--primary-soft-contrast": themeTokens.value.primarySoftContrast,
    "--bg": themeTokens.value.bg,
    "--surface": themeTokens.value.surface,
    "--text": themeTokens.value.text,
    "--muted": themeTokens.value.muted,
    "--border": themeTokens.value.border,
    "--shadow": themeTokens.value.shadow,
    "--store-primary": themeTokens.value.primary,
    "--store-primary-contrast": themeTokens.value.primaryContrast,
    "--store-primary-soft": themeTokens.value.primarySoft,
    "--store-primary-soft-contrast": themeTokens.value.primarySoftContrast,
    "--store-bg": themeTokens.value.bg,
    "--store-surface": themeTokens.value.surface,
    "--store-text": themeTokens.value.text,
    "--store-muted": themeTokens.value.muted,
    "--store-border": themeTokens.value.border,
    "--store-shadow": themeTokens.value.shadow,
    "--store-grid-columns": String(payload.value.grid_columns),
    "--store-card-height": `${payload.value.card_height}px`
  }));

  const catalogPresetConfig = computed(() =>
    normalizePresetConfig(payload.value.presets.catalog_card?.config, "catalog_card")
  );
  const productPagePresetConfig = computed(() =>
    normalizePresetConfig(payload.value.presets.product_page?.config, "product_page")
  );
  const productCardPresetConfig = computed(() =>
    normalizePresetConfig(payload.value.presets.product_card?.config, "product_card")
  );

  const belowHeaderBanners = computed(() =>
    (payload.value.banners || []).filter((item) => item.is_enabled && item.placement === "below_header")
  );

  const inGridBanners = computed(() =>
    (payload.value.banners || [])
      .filter((item) => item.is_enabled && item.placement === "in_grid")
      .sort((a, b) => {
        const rowDiff = (a.after_row || 0) - (b.after_row || 0);
        if (rowDiff !== 0) {
          return rowDiff;
        }
        return a.sort_order - b.sort_order;
      })
  );

  return {
    payload,
    loading,
    loaded,
    error,
    loadPublishedAppearance,
    themeTokens,
    storefrontCssVars,
    catalogPresetConfig,
    productPagePresetConfig,
    productCardPresetConfig,
    belowHeaderBanners,
    inGridBanners
  };
});
