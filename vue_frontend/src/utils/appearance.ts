import type {
  AppearanceBlockType,
  AppearancePresetConfig,
  AppearancePresetType
} from "../api/appearance";

const BLOCK_TYPES: AppearanceBlockType[] = [
  "title",
  "price",
  "rating",
  "reviews_count",
  "buy_button",
  "short_description"
];

const DEFAULT_VISIBILITY: Record<AppearancePresetType, Record<AppearanceBlockType, boolean>> = {
  catalog_card: {
    title: true,
    price: true,
    rating: true,
    reviews_count: true,
    buy_button: true,
    short_description: false
  },
  product_page: {
    title: true,
    price: true,
    rating: true,
    reviews_count: true,
    buy_button: true,
    short_description: true
  },
  product_card: {
    title: true,
    price: true,
    rating: true,
    reviews_count: true,
    buy_button: true,
    short_description: false
  }
};

const DEFAULT_LAYOUT: Record<AppearancePresetType, AppearancePresetConfig["layout_mode"]> = {
  catalog_card: "media_top",
  product_page: "media_left",
  product_card: "compact"
};

const DEFAULT_PHOTO_MODE: Record<AppearancePresetType, AppearancePresetConfig["photo_mode"]> = {
  catalog_card: "hover_carousel",
  product_page: "thumbnails_bottom",
  product_card: "thumbnails_bottom"
};

export const spacingLevelToPixels = (level: number) => {
  const map = [8, 12, 16, 20, 24, 28];
  const normalized = Number.isFinite(level) ? Math.min(5, Math.max(0, Math.round(level))) : 2;
  return map[normalized] || 16;
};

const normalizeHex = (value: string) => {
  const candidate = String(value || "").trim();
  if (/^#[0-9a-fA-F]{6}$/.test(candidate)) {
    return candidate.toLowerCase();
  }
  return "#ff6b00";
};

const hexToRgb = (hex: string) => {
  const base = normalizeHex(hex).slice(1);
  return {
    r: parseInt(base.slice(0, 2), 16),
    g: parseInt(base.slice(2, 4), 16),
    b: parseInt(base.slice(4, 6), 16)
  };
};

const toLinearChannel = (channel: number) => {
  const value = channel / 255;
  if (value <= 0.03928) {
    return value / 12.92;
  }
  return ((value + 0.055) / 1.055) ** 2.4;
};

const relativeLuminance = (hex: string) => {
  const rgb = hexToRgb(hex);
  return (
    0.2126 * toLinearChannel(rgb.r) + 0.7152 * toLinearChannel(rgb.g) + 0.0722 * toLinearChannel(rgb.b)
  );
};

const contrastRatio = (foregroundHex: string, backgroundHex: string) => {
  const l1 = relativeLuminance(foregroundHex);
  const l2 = relativeLuminance(backgroundHex);
  const lighter = Math.max(l1, l2);
  const darker = Math.min(l1, l2);
  return (lighter + 0.05) / (darker + 0.05);
};

const mixHexColors = (firstHex: string, secondHex: string, firstWeight = 0.5) => {
  const clampedWeight = Math.max(0, Math.min(1, firstWeight));
  const rgbA = hexToRgb(firstHex);
  const rgbB = hexToRgb(secondHex);
  const channels = ["r", "g", "b"].map((channel) => {
    const blended = Math.round(rgbA[channel as keyof typeof rgbA] * clampedWeight + rgbB[channel as keyof typeof rgbB] * (1 - clampedWeight));
    return blended.toString(16).padStart(2, "0");
  });
  return `#${channels.join("")}`;
};

export const pickReadableTextColor = (backgroundHex: string) => {
  const white = "#ffffff";
  const dark = "#111111";
  return contrastRatio(white, backgroundHex) >= contrastRatio(dark, backgroundHex) ? white : dark;
};

export const buildThemeTokens = (themeMode: "light" | "dark", primaryColor: string) => {
  const primary = normalizeHex(primaryColor);
  const palette =
    themeMode === "dark"
      ? {
          bg: "#0f1115",
          surface: "#171b22",
          text: "#f3f5f9",
          muted: "#b7bfcd",
          border: "#2a303a",
          shadow: "0 10px 24px rgba(0, 0, 0, 0.42)"
        }
      : {
          bg: "#f5f6f8",
          surface: "#ffffff",
          text: "#171923",
          muted: "#5b6473",
          border: "#d8dde7",
          shadow: "0 8px 24px rgba(18, 28, 45, 0.1)"
        };

  const primarySoft =
    themeMode === "dark" ? mixHexColors(primary, palette.bg, 0.34) : mixHexColors(primary, palette.surface, 0.16);

  return {
    primary,
    primaryContrast: pickReadableTextColor(primary),
    primarySoft,
    primarySoftContrast: pickReadableTextColor(primarySoft),
    bg: palette.bg,
    surface: palette.surface,
    text: palette.text,
    muted: palette.muted,
    border: palette.border,
    shadow: palette.shadow
  };
};

export const defaultPresetConfig = (presetType: AppearancePresetType): AppearancePresetConfig => ({
  layout_mode: DEFAULT_LAYOUT[presetType],
  photo_mode: DEFAULT_PHOTO_MODE[presetType],
  blocks: BLOCK_TYPES.map((type, index) => ({
    type,
    visible: DEFAULT_VISIBILITY[presetType][type],
    order: index
  }))
});

export const normalizePresetConfig = (
  config: AppearancePresetConfig | null | undefined,
  presetType: AppearancePresetType
): AppearancePresetConfig => {
  const fallback = defaultPresetConfig(presetType);
  if (!config) {
    return fallback;
  }

  const byType = new Map<AppearanceBlockType, { visible: boolean; order: number }>();
  fallback.blocks.forEach((block) => {
    byType.set(block.type, { visible: block.visible, order: block.order });
  });

  (config.blocks || []).forEach((block) => {
    if (!BLOCK_TYPES.includes(block.type)) {
      return;
    }
    byType.set(block.type, {
      visible: Boolean(block.visible),
      order: Number.isFinite(block.order) ? Number(block.order) : byType.get(block.type)?.order || 0
    });
  });

  const sorted = Array.from(byType.entries())
    .sort((a, b) => {
      if (a[1].order === b[1].order) {
        return BLOCK_TYPES.indexOf(a[0]) - BLOCK_TYPES.indexOf(b[0]);
      }
      return a[1].order - b[1].order;
    })
    .map(([type, item], index) => ({ type, visible: item.visible, order: index }));

  return {
    layout_mode: ["media_left", "media_top", "compact"].includes(config.layout_mode)
      ? config.layout_mode
      : fallback.layout_mode,
    photo_mode: ["thumbnails_right", "thumbnails_bottom", "hover_carousel"].includes(config.photo_mode)
      ? config.photo_mode
      : fallback.photo_mode,
    blocks: sorted
  };
};

export const visibleBlocks = (config: AppearancePresetConfig) =>
  [...config.blocks].filter((block) => block.visible).sort((a, b) => a.order - b.order);
