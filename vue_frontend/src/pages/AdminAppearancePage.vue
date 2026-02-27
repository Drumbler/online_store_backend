<template>
  <section class="page">
    <header class="heading">
      <div>
        <h1>Appearance</h1>
        <p>Draft editor with live preview. Publish applies globally.</p>
      </div>
      <div class="top-actions">
        <button :disabled="busy || !draft" @click="handlePublish">Apply</button>
        <button class="secondary" :disabled="busy || !draft" @click="handleReset">Reset draft</button>
      </div>
    </header>

    <p v-if="toast" class="toast" :class="{ error: toastType === 'error' }">{{ toast }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="loading && !draft" class="loading">Loading appearance settings...</div>

    <div v-else-if="draft" class="layout">
      <div class="editor">
        <section class="card">
          <h2>Theme</h2>
          <label>
            <span>Mode</span>
            <select v-model="draft.theme_mode">
              <option value="light">Light</option>
              <option value="dark">Dark</option>
            </select>
          </label>
          <label>
            <span>Primary color</span>
            <div class="color-row">
              <input v-model="draft.primary_color" type="color" />
              <input v-model="draft.primary_color" type="text" placeholder="#RRGGBB" />
            </div>
          </label>

          <div class="logo-editor">
            <span>Shop logo</span>
            <div class="logo-preview-wrap">
              <img v-if="logoPreviewSrc" :src="logoPreviewSrc" alt="Logo preview" class="logo-preview" />
              <div v-else class="logo-placeholder">No logo</div>
            </div>
            <input
              type="file"
              accept=".png,.jpg,.jpeg,.webp,image/png,image/jpeg,image/webp"
              :disabled="busy"
              @change="onLogoFileChange"
            />
            <small class="hint">PNG/JPG/WebP, up to 512KB, strict square format.</small>
            <small v-if="selectedLogoName" class="hint">Selected: {{ selectedLogoName }}</small>
            <small v-if="clearLogo" class="hint danger-text">Logo will be removed on save.</small>
            <button
              v-if="logoPreviewSrc || selectedLogoName"
              type="button"
              class="danger"
              :disabled="busy"
              @click="markLogoForRemoval"
            >
              Remove logo
            </button>
          </div>
        </section>

        <section class="card">
          <h2>Grid</h2>
          <label>
            <span>Columns</span>
            <select v-model.number="draft.grid_columns">
              <option v-for="n in [2, 3, 4, 5, 6]" :key="`cols-${n}`" :value="n">{{ n }}</option>
            </select>
          </label>
          <label>
            <span>Card height: {{ draft.card_height }}px</span>
            <input v-model.number="draft.card_height" type="range" min="240" max="520" step="10" />
          </label>
          <label>
            <span>Spacing level: {{ draft.spacing_level }}</span>
            <input v-model.number="draft.spacing_level" type="range" min="0" max="5" step="1" />
          </label>
          <button :disabled="busy" @click="saveDraftSettings">Save draft settings</button>
        </section>

        <section class="card">
          <div class="section-head">
            <h2>Presets</h2>
            <button :disabled="busy" @click="openCreatePresetModal">Create</button>
          </div>

          <div class="tabs">
            <button
              v-for="tab in presetTabs"
              :key="tab.type"
              :class="{ active: activePresetTab === tab.type }"
              :disabled="busy"
              @click="activePresetTab = tab.type"
            >
              {{ tab.label }}
            </button>
          </div>

          <div class="preset-list">
            <article
              v-for="preset in activeTabPresets"
              :key="preset.id"
              class="preset-row"
              :class="{ active: preset.id === activePresetIdForTab }"
            >
              <div class="preset-main">
                <strong>{{ preset.name }}</strong>
                <span v-if="preset.id === activePresetIdForTab" class="badge">Active</span>
              </div>
              <div class="preset-actions">
                <button
                  :disabled="busy || preset.id === activePresetIdForTab"
                  @click="setActivePreset(activePresetTab, preset.id)"
                >
                  Set active
                </button>
                <button :disabled="busy" @click="openEditPresetModal(preset)">Edit</button>
                <button class="danger" :disabled="busy" @click="deletePreset(preset.id)">Delete</button>
              </div>
            </article>

            <p v-if="activeTabPresets.length === 0" class="empty">No presets for this type.</p>
          </div>
        </section>

        <section class="card">
          <div class="section-head">
            <h2>Banners</h2>
            <button :disabled="busy" @click="openCreateBannerModal">Create</button>
          </div>

          <table class="table">
            <thead>
              <tr>
                <th>Placement</th>
                <th>After row</th>
                <th>Enabled</th>
                <th>Sort</th>
                <th>Actions</th>
              </tr>
            </thead>
            <tbody>
              <tr v-for="banner in banners" :key="banner.id">
                <td>{{ banner.placement }}</td>
                <td>{{ banner.after_row || "—" }}</td>
                <td>
                  <input
                    type="checkbox"
                    :checked="banner.is_enabled"
                    :disabled="busy"
                    @change="toggleBannerEnabled(banner, ($event.target as HTMLInputElement).checked)"
                  />
                </td>
                <td>{{ banner.sort_order }}</td>
                <td class="row-actions">
                  <button :disabled="busy" @click="openEditBannerModal(banner)">Edit</button>
                  <button class="danger" :disabled="busy" @click="deleteBanner(banner.id)">Delete</button>
                </td>
              </tr>
              <tr v-if="banners.length === 0">
                <td colspan="5" class="empty">No banners configured.</td>
              </tr>
            </tbody>
          </table>
        </section>
      </div>

      <aside class="preview-panel">
        <div class="preview-head">
          <h2>Live preview (draft)</h2>
          <div class="tabs">
            <button :class="{ active: previewMode === 'catalog' }" :disabled="busy" @click="previewMode = 'catalog'">
              Catalog Preview
            </button>
            <button :class="{ active: previewMode === 'product' }" :disabled="busy" @click="previewMode = 'product'">
              Product Preview
            </button>
          </div>
        </div>

        <div class="preview-root" :style="previewStyle">
          <template v-if="previewMode === 'catalog'">
            <div class="preview-grid" :style="previewGridStyle">
              <template v-for="item in previewCatalogItems" :key="item.key">
                <article
                  v-if="item.kind === 'product'"
                  class="preview-card"
                  :class="`layout-${catalogPreviewConfig.layout_mode}`"
                >
                  <div class="preview-image-wrap">
                    <img class="preview-image" :src="item.product.image_url" :alt="item.product.title" />
                  </div>
                  <div class="preview-body">
                    <template v-for="block in catalogPreviewBlocks" :key="`${item.product.id}-${block.type}`">
                      <h3 v-if="block.type === 'title'">{{ item.product.title }}</h3>
                      <p v-else-if="block.type === 'short_description'" class="muted">
                        {{ item.product.description }}
                      </p>
                      <p v-else-if="block.type === 'price'" class="price-line">
                        {{ item.product.price }} RUB
                      </p>
                      <p v-else-if="block.type === 'rating'" class="muted">Rating: {{ item.product.rating }}</p>
                      <p v-else-if="block.type === 'reviews_count'" class="muted">
                        Reviews: {{ item.product.reviews_count }}
                      </p>
                      <button v-else-if="block.type === 'buy_button'">Buy</button>
                    </template>
                  </div>
                </article>

                <a v-else class="preview-banner" :href="item.banner.link_url" target="_blank" rel="noopener noreferrer">
                  <img :src="item.banner.image_url" alt="banner" />
                </a>
              </template>
            </div>
          </template>

          <template v-else>
            <div class="preview-product" :class="`layout-${productPagePreviewConfig.layout_mode}`">
              <div class="preview-product-media">
                <img src="https://dummyimage.com/800x600/e5e5e5/404040&text=Product" alt="preview" />
              </div>

              <div class="preview-product-details">
                <template v-for="block in productPagePreviewBlocks" :key="`page-preview-${block.type}`">
                  <h3 v-if="block.type === 'title'">Mock Product</h3>
                  <p v-else-if="block.type === 'short_description'" class="muted">
                    Lightweight preview description for product page preset.
                  </p>
                  <p v-else-if="block.type === 'price'" class="price-line">2999 RUB</p>
                  <p v-else-if="block.type === 'rating'" class="muted">Rating: 4.7</p>
                  <p v-else-if="block.type === 'reviews_count'" class="muted">Reviews: 21</p>
                  <button v-else-if="block.type === 'buy_button'">Add to cart</button>
                </template>
              </div>

              <div class="preview-product-card">
                <h4>Product card preset</h4>
                <template v-for="block in productCardPreviewBlocks" :key="`card-preview-${block.type}`">
                  <p v-if="block.type === 'title'">Mock Product</p>
                  <p v-else-if="block.type === 'short_description'" class="muted">Short preview copy.</p>
                  <p v-else-if="block.type === 'price'" class="price-line">2999 RUB</p>
                  <p v-else-if="block.type === 'rating'" class="muted">Rating: 4.7</p>
                  <p v-else-if="block.type === 'reviews_count'" class="muted">Reviews: 21</p>
                  <button v-else-if="block.type === 'buy_button'">Buy</button>
                </template>
              </div>
            </div>
          </template>
        </div>
      </aside>
    </div>

    <div v-if="presetModalOpen" class="modal" @click.self="closePresetModal">
      <div class="modal-card wide">
        <div class="modal-head">
          <h3>{{ editingPresetId ? "Edit preset" : "Create preset" }}</h3>
          <button @click="closePresetModal">Close</button>
        </div>

        <label>
          <span>Name</span>
          <input v-model="presetForm.name" type="text" />
        </label>

        <div class="grid-2">
          <label>
            <span>Layout mode</span>
            <select v-model="presetForm.config.layout_mode">
              <option value="media_left">media_left</option>
              <option value="media_top">media_top</option>
              <option value="compact">compact</option>
            </select>
          </label>

          <label>
            <span>Photo mode</span>
            <select v-model="presetForm.config.photo_mode">
              <option value="thumbnails_right">thumbnails_right</option>
              <option value="thumbnails_bottom">thumbnails_bottom</option>
              <option value="hover_carousel">hover_carousel</option>
            </select>
          </label>
        </div>

        <div class="blocks-editor">
          <h4>Blocks</h4>
          <article v-for="(block, index) in presetForm.config.blocks" :key="block.type" class="block-row">
            <label class="checkbox-row">
              <input v-model="block.visible" type="checkbox" />
              <span>{{ block.type }}</span>
            </label>
            <div class="block-actions">
              <button :disabled="index === 0" @click="moveBlock(index, -1)">↑</button>
              <button :disabled="index >= presetForm.config.blocks.length - 1" @click="moveBlock(index, 1)">↓</button>
            </div>
          </article>
        </div>

        <div class="modal-actions">
          <button :disabled="busy" @click="savePreset">Save preset</button>
        </div>
      </div>
    </div>

    <div v-if="bannerModalOpen" class="modal" @click.self="closeBannerModal">
      <div class="modal-card">
        <div class="modal-head">
          <h3>{{ editingBannerId ? "Edit banner" : "Create banner" }}</h3>
          <button @click="closeBannerModal">Close</button>
        </div>

        <label>
          <span>Image URL</span>
          <input v-model="bannerForm.image_url" type="url" placeholder="https://..." />
        </label>

        <label>
          <span>Link URL</span>
          <input v-model="bannerForm.link_url" type="url" placeholder="https://..." />
        </label>

        <label>
          <span>Placement</span>
          <select v-model="bannerForm.placement">
            <option value="below_header">below_header</option>
            <option value="in_grid">in_grid</option>
          </select>
        </label>

        <label v-if="bannerForm.placement === 'in_grid'">
          <span>After row</span>
          <input v-model.number="bannerForm.after_row" type="number" min="1" step="1" />
        </label>

        <label>
          <span>Sort order</span>
          <input v-model.number="bannerForm.sort_order" type="number" />
        </label>

        <label class="checkbox-row">
          <input v-model="bannerForm.is_enabled" type="checkbox" />
          <span>Enabled</span>
        </label>

        <div class="modal-actions">
          <button :disabled="busy" @click="saveBanner">Save banner</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";

import type {
  AppearanceBanner,
  AppearancePreset,
  AppearancePresetConfig,
  AppearancePresetType,
  DraftAppearancePayload
} from "../api/appearance";
import {
  createAppearanceBanner,
  createAppearancePreset,
  deleteAppearanceBanner,
  deleteAppearancePreset,
  getAppearanceDraft,
  listAppearanceBanners,
  listAppearancePresets,
  publishAppearanceDraft,
  resetAppearanceDraft,
  updateAppearanceBanner,
  updateAppearanceDraft,
  updateAppearancePreset
} from "../api/appearance";
import { buildThemeTokens, defaultPresetConfig, normalizePresetConfig, spacingLevelToPixels, visibleBlocks } from "../utils/appearance";

const presetTabs: Array<{ type: AppearancePresetType; label: string }> = [
  { type: "catalog_card", label: "Catalog Card" },
  { type: "product_page", label: "Product Page" },
  { type: "product_card", label: "Product Card" }
];

const mockProducts = [
  {
    id: "m-1",
    title: "Brew Kit Alpha",
    description: "Compact coffee set for daily brewing.",
    price: "2990",
    image_url: "https://dummyimage.com/600x420/d8d8d8/404040&text=Alpha",
    rating: "4.8",
    reviews_count: 21
  },
  {
    id: "m-2",
    title: "Brew Kit Beta",
    description: "Manual brewing tools with glass server.",
    price: "3590",
    image_url: "https://dummyimage.com/600x420/cccccc/404040&text=Beta",
    rating: "4.5",
    reviews_count: 14
  },
  {
    id: "m-3",
    title: "Brew Kit Gamma",
    description: "Starter pack for pour-over routine.",
    price: "1890",
    image_url: "https://dummyimage.com/600x420/e0e0e0/404040&text=Gamma",
    rating: "4.2",
    reviews_count: 8
  },
  {
    id: "m-4",
    title: "Brew Kit Delta",
    description: "Travel-friendly setup with compact grinder.",
    price: "2790",
    image_url: "https://dummyimage.com/600x420/f0f0f0/404040&text=Delta",
    rating: "4.6",
    reviews_count: 17
  }
];

const loading = ref(false);
const saving = ref(false);
const publishing = ref(false);
const resetting = ref(false);
const error = ref<string | null>(null);
const toast = ref<string | null>(null);
const toastType = ref<"ok" | "error">("ok");

const draft = ref<DraftAppearancePayload | null>(null);
const presets = ref<Record<AppearancePresetType, AppearancePreset[]>>({
  catalog_card: [],
  product_page: [],
  product_card: []
});
const banners = ref<AppearanceBanner[]>([]);

const activePresetTab = ref<AppearancePresetType>("catalog_card");
const previewMode = ref<"catalog" | "product">("catalog");

const presetModalOpen = ref(false);
const editingPresetId = ref<number | null>(null);

const presetForm = reactive<{
  preset_type: AppearancePresetType;
  name: string;
  config: AppearancePresetConfig;
}>({
  preset_type: "catalog_card",
  name: "",
  config: defaultPresetConfig("catalog_card")
});

const bannerModalOpen = ref(false);
const editingBannerId = ref<number | null>(null);
const bannerForm = reactive<Omit<AppearanceBanner, "id">>({
  image_url: "",
  link_url: "",
  placement: "below_header",
  after_row: null,
  is_enabled: true,
  sort_order: 0
});
const selectedLogoFile = ref<File | null>(null);
const logoPreviewData = ref<string | null>(null);
const clearLogo = ref(false);

const busy = computed(() => loading.value || saving.value || publishing.value || resetting.value);
const logoPreviewSrc = computed(() => {
  if (logoPreviewData.value) {
    return logoPreviewData.value;
  }
  if (clearLogo.value) {
    return "";
  }
  return draft.value?.logo_url || "";
});
const selectedLogoName = computed(() => selectedLogoFile.value?.name || "");

const activeTabPresets = computed(() => presets.value[activePresetTab.value] || []);

const activePresetIdForTab = computed(() => {
  if (!draft.value) {
    return null;
  }
  if (activePresetTab.value === "catalog_card") {
    return draft.value.active_catalog_preset_id;
  }
  if (activePresetTab.value === "product_page") {
    return draft.value.active_product_page_preset_id;
  }
  return draft.value.active_product_card_preset_id;
});

const activeCatalogPreset = computed(() => {
  const id = draft.value?.active_catalog_preset_id;
  const found = presets.value.catalog_card.find((item) => item.id === id) || presets.value.catalog_card[0];
  return found || null;
});

const activeProductPagePreset = computed(() => {
  const id = draft.value?.active_product_page_preset_id;
  const found = presets.value.product_page.find((item) => item.id === id) || presets.value.product_page[0];
  return found || null;
});

const activeProductCardPreset = computed(() => {
  const id = draft.value?.active_product_card_preset_id;
  const found = presets.value.product_card.find((item) => item.id === id) || presets.value.product_card[0];
  return found || null;
});

const catalogPreviewConfig = computed(() =>
  normalizePresetConfig(activeCatalogPreset.value?.config, "catalog_card")
);
const productPagePreviewConfig = computed(() =>
  normalizePresetConfig(activeProductPagePreset.value?.config, "product_page")
);
const productCardPreviewConfig = computed(() =>
  normalizePresetConfig(activeProductCardPreset.value?.config, "product_card")
);

const catalogPreviewBlocks = computed(() => visibleBlocks(catalogPreviewConfig.value));
const productPagePreviewBlocks = computed(() => visibleBlocks(productPagePreviewConfig.value));
const productCardPreviewBlocks = computed(() => visibleBlocks(productCardPreviewConfig.value));

const previewStyle = computed(() => {
  if (!draft.value) {
    return {};
  }
  const tokens = buildThemeTokens(draft.value.theme_mode, draft.value.primary_color);
  return {
    "--preview-primary": tokens.primary,
    "--preview-bg": tokens.bg,
    "--preview-surface": tokens.surface,
    "--preview-text": tokens.text,
    "--preview-muted": tokens.muted,
    "--preview-border": tokens.border,
    "--preview-columns": String(draft.value.grid_columns),
    "--preview-gap": `${spacingLevelToPixels(draft.value.spacing_level)}px`,
    "--preview-card-height": `${draft.value.card_height}px`
  };
});

const previewGridStyle = computed(() => ({
  gridTemplateColumns: `repeat(${Math.max(2, Math.min(6, Number(draft.value?.grid_columns || 4)))}, minmax(0, 1fr))`
}));

type PreviewCatalogItem =
  | { kind: "product"; key: string; product: (typeof mockProducts)[number] }
  | { kind: "banner"; key: string; banner: AppearanceBanner };

const previewCatalogItems = computed<PreviewCatalogItem[]>(() => {
  const items: PreviewCatalogItem[] = [];
  const columns = Math.max(2, Math.min(6, Number(draft.value?.grid_columns || 4)));
  const enabledGridBanners = banners.value
    .filter((item) => item.is_enabled && item.placement === "in_grid" && Number(item.after_row || 0) >= 1)
    .sort((a, b) => {
      const rowDiff = Number(a.after_row || 0) - Number(b.after_row || 0);
      if (rowDiff !== 0) {
        return rowDiff;
      }
      return a.sort_order - b.sort_order;
    });

  const bannerByRow = new Map<number, AppearanceBanner[]>();
  enabledGridBanners.forEach((banner) => {
    const row = Number(banner.after_row || 0);
    const rowItems = bannerByRow.get(row) || [];
    rowItems.push(banner);
    bannerByRow.set(row, rowItems);
  });

  let renderedRows = 0;
  mockProducts.forEach((product, index) => {
    items.push({ kind: "product", key: `p-${product.id}`, product });
    if ((index + 1) % columns === 0) {
      renderedRows += 1;
      const rowBanners = bannerByRow.get(renderedRows) || [];
      rowBanners.forEach((banner, rowIndex) => {
        items.push({ kind: "banner", key: `b-${banner.id}-${renderedRows}-${rowIndex}`, banner });
      });
    }
  });

  const totalRows = Math.ceil(mockProducts.length / columns);
  if (totalRows > renderedRows) {
    const rowBanners = bannerByRow.get(totalRows) || [];
    rowBanners.forEach((banner, rowIndex) => {
      items.push({ kind: "banner", key: `b-${banner.id}-${totalRows}-${rowIndex}`, banner });
    });
  }

  return items;
});

const showToast = (message: string, type: "ok" | "error" = "ok") => {
  toastType.value = type;
  toast.value = message;
  window.setTimeout(() => {
    if (toast.value === message) {
      toast.value = null;
    }
  }, 3200);
};

const resetLogoState = () => {
  selectedLogoFile.value = null;
  logoPreviewData.value = null;
  clearLogo.value = false;
};

const onLogoFileChange = (event: Event) => {
  const input = event.target as HTMLInputElement;
  const file = input.files?.[0] || null;
  selectedLogoFile.value = file;
  clearLogo.value = false;

  if (!file) {
    logoPreviewData.value = null;
    return;
  }

  const reader = new FileReader();
  reader.onload = () => {
    logoPreviewData.value = typeof reader.result === "string" ? reader.result : null;
  };
  reader.readAsDataURL(file);
};

const markLogoForRemoval = () => {
  selectedLogoFile.value = null;
  logoPreviewData.value = null;
  clearLogo.value = true;
};

const fetchDraft = async () => {
  const response = await getAppearanceDraft();
  draft.value = response.data;
  resetLogoState();
};

const fetchPresets = async () => {
  const [catalog, productPage, productCard] = await Promise.all([
    listAppearancePresets("catalog_card"),
    listAppearancePresets("product_page"),
    listAppearancePresets("product_card")
  ]);

  presets.value = {
    catalog_card: catalog.data?.results || [],
    product_page: productPage.data?.results || [],
    product_card: productCard.data?.results || []
  };
};

const fetchBanners = async () => {
  const response = await listAppearanceBanners();
  banners.value = response.data?.results || [];
};

const loadAll = async () => {
  loading.value = true;
  error.value = null;
  try {
    await Promise.all([fetchDraft(), fetchPresets(), fetchBanners()]);
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to load appearance data.";
  } finally {
    loading.value = false;
  }
};

const saveDraftSettings = async () => {
  if (!draft.value) {
    return false;
  }

  saving.value = true;
  error.value = null;
  try {
    const hasLogoPatch = Boolean(selectedLogoFile.value) || clearLogo.value;
    let payload: FormData | Partial<DraftAppearancePayload>;

    if (hasLogoPatch) {
      const formData = new FormData();
      formData.append("theme_mode", draft.value.theme_mode);
      formData.append("primary_color", draft.value.primary_color);
      formData.append("grid_columns", String(draft.value.grid_columns));
      formData.append("card_height", String(draft.value.card_height));
      formData.append("spacing_level", String(draft.value.spacing_level));

      if (draft.value.active_catalog_preset_id !== null) {
        formData.append("active_catalog_preset_id", String(draft.value.active_catalog_preset_id));
      }
      if (draft.value.active_product_page_preset_id !== null) {
        formData.append(
          "active_product_page_preset_id",
          String(draft.value.active_product_page_preset_id)
        );
      }
      if (draft.value.active_product_card_preset_id !== null) {
        formData.append(
          "active_product_card_preset_id",
          String(draft.value.active_product_card_preset_id)
        );
      }

      if (selectedLogoFile.value) {
        formData.append("logo", selectedLogoFile.value);
      }
      if (clearLogo.value) {
        formData.append("clear_logo", "true");
      }

      payload = formData;
    } else {
      payload = {
        theme_mode: draft.value.theme_mode,
        primary_color: draft.value.primary_color,
        grid_columns: draft.value.grid_columns,
        card_height: draft.value.card_height,
        spacing_level: draft.value.spacing_level,
        active_catalog_preset_id: draft.value.active_catalog_preset_id,
        active_product_page_preset_id: draft.value.active_product_page_preset_id,
        active_product_card_preset_id: draft.value.active_product_card_preset_id
      };
    }

    const response = await updateAppearanceDraft(payload);
    draft.value = response.data;
    resetLogoState();
    showToast("Draft settings saved.");
    return true;
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to save draft settings.";
    return false;
  } finally {
    saving.value = false;
  }
};

const setActivePreset = async (type: AppearancePresetType, presetId: number) => {
  if (!draft.value) {
    return;
  }

  const payload: Partial<DraftAppearancePayload> = {};
  if (type === "catalog_card") {
    payload.active_catalog_preset_id = presetId;
  }
  if (type === "product_page") {
    payload.active_product_page_preset_id = presetId;
  }
  if (type === "product_card") {
    payload.active_product_card_preset_id = presetId;
  }

  saving.value = true;
  error.value = null;
  try {
    const response = await updateAppearanceDraft(payload);
    draft.value = response.data;
    showToast("Active preset updated.");
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to set active preset.";
  } finally {
    saving.value = false;
  }
};

const openCreatePresetModal = () => {
  editingPresetId.value = null;
  presetForm.preset_type = activePresetTab.value;
  presetForm.name = "";
  presetForm.config = defaultPresetConfig(activePresetTab.value);
  presetModalOpen.value = true;
};

const openEditPresetModal = (preset: AppearancePreset) => {
  editingPresetId.value = preset.id;
  presetForm.preset_type = preset.preset_type;
  presetForm.name = preset.name;
  presetForm.config = normalizePresetConfig(preset.config, preset.preset_type);
  presetModalOpen.value = true;
};

const closePresetModal = () => {
  presetModalOpen.value = false;
};

const moveBlock = (index: number, delta: number) => {
  const target = index + delta;
  if (target < 0 || target >= presetForm.config.blocks.length) {
    return;
  }

  const copy = [...presetForm.config.blocks];
  const [block] = copy.splice(index, 1);
  copy.splice(target, 0, block);
  presetForm.config.blocks = copy.map((item, itemIndex) => ({ ...item, order: itemIndex }));
};

const savePreset = async () => {
  if (!presetForm.name.trim()) {
    error.value = "Preset name is required.";
    return;
  }

  saving.value = true;
  error.value = null;
  try {
    const normalizedConfig = normalizePresetConfig(presetForm.config, presetForm.preset_type);
    if (editingPresetId.value) {
      await updateAppearancePreset(editingPresetId.value, {
        name: presetForm.name.trim(),
        config: normalizedConfig
      });
      showToast("Preset updated.");
    } else {
      await createAppearancePreset({
        preset_type: presetForm.preset_type,
        name: presetForm.name.trim(),
        config: normalizedConfig
      });
      showToast("Preset created.");
    }

    await fetchPresets();
    await fetchDraft();
    presetModalOpen.value = false;
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to save preset.";
  } finally {
    saving.value = false;
  }
};

const deletePreset = async (presetId: number) => {
  if (!window.confirm("Delete this preset?")) {
    return;
  }

  saving.value = true;
  error.value = null;
  try {
    await deleteAppearancePreset(presetId);
    await fetchPresets();
    await fetchDraft();
    showToast("Preset deleted.");
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to delete preset.";
  } finally {
    saving.value = false;
  }
};

const openCreateBannerModal = () => {
  editingBannerId.value = null;
  bannerForm.image_url = "";
  bannerForm.link_url = "";
  bannerForm.placement = "below_header";
  bannerForm.after_row = null;
  bannerForm.is_enabled = true;
  bannerForm.sort_order = 0;
  bannerModalOpen.value = true;
};

const openEditBannerModal = (banner: AppearanceBanner) => {
  editingBannerId.value = banner.id;
  bannerForm.image_url = banner.image_url;
  bannerForm.link_url = banner.link_url;
  bannerForm.placement = banner.placement;
  bannerForm.after_row = banner.after_row;
  bannerForm.is_enabled = banner.is_enabled;
  bannerForm.sort_order = banner.sort_order;
  bannerModalOpen.value = true;
};

const closeBannerModal = () => {
  bannerModalOpen.value = false;
};

const saveBanner = async () => {
  saving.value = true;
  error.value = null;
  try {
    const payload: Omit<AppearanceBanner, "id"> = {
      image_url: bannerForm.image_url,
      link_url: bannerForm.link_url,
      placement: bannerForm.placement,
      after_row: bannerForm.placement === "in_grid" ? bannerForm.after_row : null,
      is_enabled: bannerForm.is_enabled,
      sort_order: bannerForm.sort_order
    };

    if (editingBannerId.value) {
      await updateAppearanceBanner(editingBannerId.value, payload);
      showToast("Banner updated.");
    } else {
      await createAppearanceBanner(payload);
      showToast("Banner created.");
    }

    await fetchBanners();
    bannerModalOpen.value = false;
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to save banner.";
  } finally {
    saving.value = false;
  }
};

const deleteBanner = async (bannerId: number) => {
  if (!window.confirm("Delete this banner?")) {
    return;
  }

  saving.value = true;
  error.value = null;
  try {
    await deleteAppearanceBanner(bannerId);
    await fetchBanners();
    showToast("Banner deleted.");
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to delete banner.";
  } finally {
    saving.value = false;
  }
};

const toggleBannerEnabled = async (banner: AppearanceBanner, nextValue: boolean) => {
  saving.value = true;
  error.value = null;
  try {
    await updateAppearanceBanner(banner.id, { is_enabled: nextValue });
    banner.is_enabled = nextValue;
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to update banner.";
  } finally {
    saving.value = false;
  }
};

const handlePublish = async () => {
  if (!draft.value) {
    return;
  }

  publishing.value = true;
  error.value = null;
  try {
    const saved = await saveDraftSettings();
    if (!saved) {
      return;
    }
    await publishAppearanceDraft();
    showToast("Draft published.");
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to publish draft.";
  } finally {
    publishing.value = false;
  }
};

const handleReset = async () => {
  resetting.value = true;
  error.value = null;
  try {
    await resetAppearanceDraft();
    await loadAll();
    showToast("Draft reset to published.");
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to reset draft.";
  } finally {
    resetting.value = false;
  }
};

onMounted(async () => {
  await loadAll();
});
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.heading {
  display: flex;
  justify-content: space-between;
  align-items: flex-end;
  gap: 12px;
}

.heading p {
  margin: 4px 0 0;
  color: #6f5f4c;
}

.top-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.top-actions .secondary {
  background: #eee6d8;
}

.layout {
  display: grid;
  grid-template-columns: minmax(460px, 1.1fr) minmax(420px, 1fr);
  gap: 16px;
}

.editor,
.preview-panel {
  display: flex;
  flex-direction: column;
  gap: 12px;
  min-width: 0;
}

.card {
  border: 1px solid #dccfb9;
  background: #fffdf8;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.section-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.color-row {
  display: flex;
  gap: 8px;
}

.logo-editor {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.logo-preview-wrap {
  width: 120px;
  height: 120px;
  border: 1px solid #e8dcc8;
  border-radius: 12px;
  overflow: hidden;
  background: #fff;
}

.logo-preview {
  width: 100%;
  height: 100%;
  object-fit: cover;
  display: block;
}

.logo-placeholder {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #857864;
  font-size: 13px;
}

.hint {
  color: #6f5f4c;
  font-size: 12px;
}

.danger-text {
  color: #a02626;
}

.tabs {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.tabs button.active {
  background: #e7d6bc;
  font-weight: 600;
}

.preset-list {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preset-row {
  border: 1px solid #e8dcc8;
  background: #fff;
  padding: 10px;
  display: flex;
  justify-content: space-between;
  gap: 12px;
  align-items: center;
}

.preset-row.active {
  border-color: #b58b45;
}

.preset-main {
  display: flex;
  align-items: center;
  gap: 8px;
}

.badge {
  border: 1px solid #b58b45;
  background: #f4ebdc;
  border-radius: 999px;
  font-size: 12px;
  padding: 2px 8px;
}

.preset-actions,
.row-actions {
  display: flex;
  gap: 6px;
  flex-wrap: wrap;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th,
.table td {
  border-bottom: 1px solid #ebdfcb;
  padding: 8px;
  text-align: left;
}

.preview-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.preview-root {
  border: 1px solid var(--preview-border, #ccc);
  background: var(--preview-bg, #f7f7f7);
  color: var(--preview-text, #222);
  border-radius: 12px;
  padding: 12px;
  min-height: 540px;
}

.preview-grid {
  display: grid;
  grid-template-columns: repeat(var(--preview-columns, 4), minmax(0, 1fr));
  gap: var(--preview-gap, 16px);
}

.preview-card {
  background: var(--preview-surface, #fff);
  border: 1px solid var(--preview-border, #ddd);
  min-height: var(--preview-card-height, 320px);
  display: flex;
  flex-direction: column;
}

.preview-card.layout-media_left {
  flex-direction: row;
}

.preview-image-wrap {
  display: block;
}

.preview-image {
  width: 100%;
  height: 160px;
  object-fit: cover;
  display: block;
}

.preview-body {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.preview-body h3 {
  margin: 0;
  font-size: 16px;
}

.preview-body button,
.preview-product-details button,
.preview-product-card button {
  margin-top: auto;
}

.preview-banner {
  grid-column: 1 / -1;
  display: block;
  border: 1px solid var(--preview-border, #ddd);
  border-radius: 8px;
  overflow: hidden;
}

.preview-banner img {
  width: 100%;
  max-height: 180px;
  object-fit: cover;
  display: block;
}

.preview-product {
  display: grid;
  grid-template-columns: 1.3fr 1fr 280px;
  gap: 12px;
}

.preview-product.layout-media_top {
  grid-template-columns: 1fr;
}

.preview-product.layout-compact {
  grid-template-columns: 1fr 280px;
}

.preview-product-media,
.preview-product-details,
.preview-product-card {
  border: 1px solid var(--preview-border, #ddd);
  background: var(--preview-surface, #fff);
  border-radius: 10px;
  padding: 10px;
}

.preview-product-media img {
  width: 100%;
  height: 220px;
  object-fit: cover;
}

.preview-product-details,
.preview-product-card {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.price-line {
  font-weight: 700;
  color: var(--preview-primary, #ff6b00);
}

.muted {
  color: var(--preview-muted, #666);
  margin: 0;
}

.toast {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid #aacb9f;
  background: #eff9ea;
}

.toast.error {
  border-color: #e59f9f;
  background: #fff0f0;
}

.error {
  margin: 0;
  color: #b82222;
}

.loading {
  padding: 14px;
  border: 1px dashed #c8b79f;
  background: #fffdf8;
}

.empty {
  color: #6f5f4c;
  text-align: center;
}

.danger {
  color: #a02626;
}

.modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  z-index: 50;
}

.modal-card {
  width: min(640px, 100%);
  background: #fff;
  border: 1px solid #d9ceb8;
  border-radius: 12px;
  padding: 14px;
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-height: 92vh;
  overflow: auto;
}

.modal-card.wide {
  width: min(760px, 100%);
}

.modal-head {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 10px;
}

.grid-2 {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 10px;
}

.blocks-editor {
  border: 1px solid #eadfc9;
  background: #fffbf4;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.block-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  border: 1px solid #eee3cf;
  background: #fff;
  padding: 6px 8px;
}

.checkbox-row {
  display: inline-flex;
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.block-actions,
.modal-actions {
  display: flex;
  gap: 6px;
  justify-content: flex-end;
}

@media (max-width: 1360px) {
  .layout {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 740px) {
  .grid-2 {
    grid-template-columns: 1fr;
  }

  .preview-grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }

  .preview-product,
  .preview-product.layout-compact {
    grid-template-columns: 1fr;
  }
}

@media (max-width: 520px) {
  .preview-grid {
    grid-template-columns: 1fr;
  }
}
</style>
