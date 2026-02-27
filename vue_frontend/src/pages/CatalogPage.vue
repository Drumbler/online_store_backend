<template>
  <section class="page bg-app text-app">
    <h1>Catalog</h1>

    <form class="search-panel" @submit.prevent="applyFilters">
      <label class="search-label" for="search">Search products</label>
      <div class="search-row">
        <input id="search" v-model="search" class="search-input" placeholder="Search by title" />
        <button type="submit" class="btn btn-primary">Search</button>
        <button
          v-if="hasActiveFilters"
          type="button"
          class="btn btn-outline"
          @click="resetFilters"
        >
          Reset
        </button>
      </div>
    </form>

    <div class="layout">
      <aside class="categories">
        <h2>Categories</h2>
        <button
          type="button"
          class="category-btn"
          :class="{ active: !selectedCategory }"
          @click="setCategory('')"
        >
          All
        </button>
        <button
          v-for="category in catalogStore.categories"
          :key="category.id"
          type="button"
          class="category-btn"
          :class="{ active: category.slug === selectedCategory }"
          @click="setCategory(category.slug || '')"
        >
          {{ category.title || category.slug || category.id }}
        </button>
      </aside>

      <section class="products">
        <div class="products-toolbar">
          <span class="results-count">{{ catalogStore.pagination.total || 0 }} items</span>

          <div ref="sortMenuRef" class="sort-wrap">
            <button
              type="button"
              class="btn btn-neutral sort-trigger"
              :aria-expanded="sortMenuOpen ? 'true' : 'false'"
              aria-haspopup="menu"
              @click="toggleSortMenu"
            >
              Сортировка
              <span class="sort-current">{{ activeSortLabel }}</span>
              <svg
                class="sort-caret"
                :class="{ open: sortMenuOpen }"
                viewBox="0 0 24 24"
                role="img"
                aria-hidden="true"
                focusable="false"
              >
                <path d="M7 10l5 5 5-5z" fill="currentColor" />
              </svg>
            </button>

            <div v-if="sortMenuOpen" class="sort-menu" role="menu" aria-label="Sort options">
              <button
                v-for="option in sortOptions"
                :key="option.value || 'default'"
                type="button"
                class="sort-option"
                :class="{ active: option.value === ordering }"
                role="menuitemradio"
                :aria-checked="option.value === ordering ? 'true' : 'false'"
                @click="applySortOption(option.value)"
              >
                {{ option.label }}
              </button>
            </div>
          </div>
        </div>

        <div v-if="catalogStore.loading" class="state-box">Loading...</div>
        <div v-else-if="catalogStore.error" class="state-box error">{{ catalogStore.error }}</div>

        <div v-else class="grid" :style="gridStyle">
          <template v-for="item in gridItems" :key="gridItemKey(item)">
            <article
              v-if="item.kind === 'product'"
              class="card"
              :class="[`layout-${catalogPreset.layout_mode}`, `photo-${catalogPreset.photo_mode}`]"
              :style="cardStyle"
            >
              <RouterLink :to="`/p/${item.product.slug}`" class="card-link media-wrap">
                <img
                  v-if="item.product.image_url"
                  :src="item.product.image_url"
                  :alt="item.product.title"
                  class="card-image"
                />
                <div v-else class="card-placeholder">No image</div>
              </RouterLink>

              <div class="card-body">
                <template v-for="block in visibleCatalogBlocks" :key="`block-${item.product.id}-${block.type}`">
                  <h3 v-if="block.type === 'title'" class="title">{{ item.product.title }}</h3>

                  <p v-else-if="block.type === 'short_description'" class="short-description">
                    {{ shortDescription(item.product.description) }}
                  </p>

                  <div v-else-if="block.type === 'price'" class="price">
                    <template v-if="hasDiscount(item.product)">
                      <span class="old">{{ item.product.price }} {{ item.product.currency }}</span>
                      <span class="new">{{ discountedPrice(item.product) }} {{ item.product.currency }}</span>
                      <span class="badge">-{{ item.product.discount_percent }}%</span>
                    </template>
                    <template v-else>
                      <span>{{ item.product.price }} {{ item.product.currency }}</span>
                    </template>
                  </div>

                  <div v-else-if="block.type === 'rating'" class="rating-summary">
                    <template v-if="hasReviews(item.product.id)">
                      <StarRatingDisplay :rating="getProductSummary(item.product.id).avg_rating" />
                      <span>{{ getProductSummary(item.product.id).avg_rating?.toFixed(1) }}</span>
                    </template>
                    <template v-else>
                      <span class="rating-empty">—</span>
                    </template>
                  </div>

                  <div v-else-if="block.type === 'reviews_count'" class="reviews-count">
                    {{ reviewsCountText(item.product.id) }}
                  </div>

                  <button
                    v-else-if="block.type === 'buy_button'"
                    type="button"
                    class="btn btn-primary buy-btn"
                    @click="addToCart(item.product.id)"
                  >
                    Add to cart
                  </button>
                </template>
              </div>
            </article>

            <a
              v-else
              class="grid-banner"
              :href="item.banner.link_url"
              target="_blank"
              rel="noopener noreferrer"
            >
              <img class="grid-banner-image" :src="item.banner.image_url" alt="Catalog banner" />
            </a>
          </template>
        </div>

        <div class="pagination">
          <button type="button" class="btn btn-neutral" :disabled="page <= 1" @click="changePage(page - 1)">
            Prev
          </button>
          <span>Page {{ page }} of {{ totalPages }}</span>
          <button
            type="button"
            class="btn btn-neutral"
            :disabled="page >= totalPages"
            @click="changePage(page + 1)"
          >
            Next
          </button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";

import type { AppearanceBanner } from "../api/appearance";
import { getReviewsSummary, type ReviewRatingSummary } from "../api/public";
import StarRatingDisplay from "../components/StarRatingDisplay.vue";
import { useAppearanceStore } from "../stores/appearance";
import { useCartStore } from "../stores/cart";
import { useCatalogStore } from "../stores/catalog";
import { spacingLevelToPixels, visibleBlocks } from "../utils/appearance";

const router = useRouter();
const route = useRoute();
const catalogStore = useCatalogStore();
const cartStore = useCartStore();
const appearanceStore = useAppearanceStore();

const search = ref("");
const ordering = ref("");
const selectedCategory = ref("");
const ratingSummaries = ref<Record<string, ReviewRatingSummary>>({});
const sortMenuOpen = ref(false);
const sortMenuRef = ref<HTMLElement | null>(null);
let ratingRequestId = 0;

const sortOptions = [
  { value: "", label: "По умолчанию" },
  { value: "price", label: "Цена: по возрастанию" },
  { value: "-price", label: "Цена: по убыванию" },
  { value: "title", label: "Название: A-Z" },
  { value: "-title", label: "Название: Z-A" }
];

const page = computed(() => catalogStore.pagination.page || 1);
const totalPages = computed(() => {
  const total = catalogStore.pagination.total || 0;
  const pageSize = catalogStore.pagination.page_size || 1;
  return Math.max(1, Math.ceil(total / pageSize));
});

const hasActiveFilters = computed(
  () => Boolean(search.value.trim() || ordering.value || selectedCategory.value)
);
const activeSortLabel = computed(
  () => sortOptions.find((option) => option.value === ordering.value)?.label || "По умолчанию"
);

const gridColumns = computed(() => {
  const value = Number(appearanceStore.payload.grid_columns || 4);
  return Math.max(2, Math.min(6, value));
});

const gridGapPx = computed(() => spacingLevelToPixels(appearanceStore.payload.spacing_level));

const catalogPreset = computed(() => appearanceStore.catalogPresetConfig);
const visibleCatalogBlocks = computed(() => visibleBlocks(catalogPreset.value));
const inGridBanners = computed(() => appearanceStore.inGridBanners);

const gridStyle = computed(() => ({
  "--grid-columns": String(gridColumns.value),
  "--grid-gap": `${gridGapPx.value}px`
}));

const cardStyle = computed(() => ({
  "--card-height": `${appearanceStore.payload.card_height || 320}px`
}));

type GridItem =
  | { kind: "product"; product: any }
  | { kind: "banner"; banner: AppearanceBanner; key: string };

const gridItems = computed<GridItem[]>(() => {
  const result: GridItem[] = [];
  const products = catalogStore.products || [];
  const columns = gridColumns.value;

  if (products.length === 0) {
    return result;
  }

  const bannerByRow = new Map<number, AppearanceBanner[]>();
  inGridBanners.value.forEach((banner) => {
    const row = Number(banner.after_row || 0);
    if (row < 1) {
      return;
    }
    const existing = bannerByRow.get(row) || [];
    existing.push(banner);
    bannerByRow.set(row, existing);
  });

  let renderedRows = 0;
  products.forEach((product, index) => {
    result.push({ kind: "product", product });
    if ((index + 1) % columns === 0) {
      renderedRows += 1;
      const rowBanners = bannerByRow.get(renderedRows) || [];
      rowBanners.forEach((banner, bannerIndex) => {
        result.push({
          kind: "banner",
          banner,
          key: `${banner.id}-${renderedRows}-${bannerIndex}`
        });
      });
    }
  });

  const totalRows = Math.ceil(products.length / columns);
  if (totalRows > renderedRows) {
    const rowBanners = bannerByRow.get(totalRows) || [];
    rowBanners.forEach((banner, bannerIndex) => {
      result.push({
        kind: "banner",
        banner,
        key: `${banner.id}-${totalRows}-${bannerIndex}`
      });
    });
  }

  return result;
});

const gridItemKey = (item: GridItem) => {
  if (item.kind === "product") {
    return `product-${item.product.id}`;
  }
  return `banner-${item.key}`;
};

const normalizeQuery = () => {
  search.value = typeof route.query.search === "string" ? route.query.search : "";
  ordering.value = typeof route.query.ordering === "string" ? route.query.ordering : "";
  selectedCategory.value = typeof route.query.category === "string" ? route.query.category : "";
};

const applyFilters = () => {
  const query: Record<string, string> = {};
  if (search.value.trim()) {
    query.search = search.value.trim();
  }
  if (ordering.value) {
    query.ordering = ordering.value;
  }
  if (selectedCategory.value) {
    query.category = selectedCategory.value;
  }
  query.page = "1";
  router.push({ path: "/", query });
};

const resetFilters = () => {
  search.value = "";
  ordering.value = "";
  selectedCategory.value = "";
  applyFilters();
};

const setCategory = (slug: string) => {
  selectedCategory.value = slug;
  applyFilters();
};

const toggleSortMenu = () => {
  sortMenuOpen.value = !sortMenuOpen.value;
};

const applySortOption = (value: string) => {
  ordering.value = value;
  sortMenuOpen.value = false;
  applyFilters();
};

const onGlobalClick = (event: MouseEvent) => {
  if (!sortMenuOpen.value) {
    return;
  }
  const target = event.target as Node | null;
  if (sortMenuRef.value && target && !sortMenuRef.value.contains(target)) {
    sortMenuOpen.value = false;
  }
};

const changePage = (nextPage: number) => {
  const query = { ...route.query, page: String(nextPage) };
  router.push({ path: "/", query });
};

const addToCart = (productId?: string) => {
  if (!productId) {
    return;
  }
  cartStore.addToCart(productId, 1);
};

const getProductSummary = (productId?: string): ReviewRatingSummary => {
  if (!productId) {
    return { avg_rating: null, reviews_count: 0 };
  }
  return ratingSummaries.value[productId] || { avg_rating: null, reviews_count: 0 };
};

const hasReviews = (productId?: string) => getProductSummary(productId).reviews_count > 0;

const reviewsCountText = (productId?: string) => {
  const count = getProductSummary(productId).reviews_count;
  if (count <= 0) {
    return "No reviews";
  }
  return `${count} review${count === 1 ? "" : "s"}`;
};

const hasDiscount = (product: any) => {
  const discount = Number(product.discount_percent || 0);
  return discount > 0;
};

const discountedPrice = (product: any) => {
  if (product.discounted_price) {
    return product.discounted_price;
  }
  const price = Number(product.price || 0);
  const discount = Number(product.discount_percent || 0);
  const discounted = price * (1 - discount / 100);
  return discounted.toFixed(2);
};

const shortDescription = (description?: string | null) => {
  if (!description) {
    return "No description";
  }
  if (description.length <= 120) {
    return description;
  }
  return `${description.slice(0, 117)}...`;
};

onMounted(() => {
  catalogStore.fetchCategories();
  void appearanceStore.loadPublishedAppearance();
  document.addEventListener("click", onGlobalClick);
});

onUnmounted(() => {
  document.removeEventListener("click", onGlobalClick);
});

const fetchRatingSummaries = async () => {
  const productIds = catalogStore.products.map((item) => item.id).filter(Boolean);
  if (productIds.length === 0) {
    ratingSummaries.value = {};
    return;
  }

  const requestId = ++ratingRequestId;
  try {
    const response = await getReviewsSummary(productIds);
    if (requestId !== ratingRequestId) {
      return;
    }
    ratingSummaries.value = response.data?.results || {};
  } catch {
    if (requestId !== ratingRequestId) {
      return;
    }
    ratingSummaries.value = {};
  }
};

watch(
  () => route.query,
  async (query) => {
    normalizeQuery();
    sortMenuOpen.value = false;
    await catalogStore.fetchProductsFromRouteQuery(query);
    await fetchRatingSummaries();
  },
  { immediate: true }
);
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.search-panel {
  border: 1px solid var(--border);
  border-radius: 16px;
  padding: 14px;
  background: var(--surface);
  box-shadow: var(--shadow);
}

.search-label {
  display: inline-block;
  margin-bottom: 8px;
  color: var(--muted);
  font-weight: 600;
}

.search-row {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

.search-input {
  flex: 1;
  min-width: 220px;
}

.layout {
  display: grid;
  grid-template-columns: 230px 1fr;
  gap: 24px;
}

.categories {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 14px;
  border-radius: 14px;
  border: 1px solid var(--border);
  background: var(--surface);
  box-shadow: var(--shadow);
}

.category-btn {
  text-align: left;
  justify-content: flex-start;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
}

.category-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
}

.category-btn.active {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 12%, transparent);
  color: var(--primary);
}

.products {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.products-toolbar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
}

.results-count {
  color: var(--muted);
  font-weight: 600;
}

.sort-wrap {
  position: relative;
}

.sort-trigger {
  min-height: 40px;
  gap: 8px;
}

.sort-current {
  color: var(--muted);
  font-weight: 500;
}

.sort-caret {
  width: 18px;
  height: 18px;
  transition: transform 0.2s ease;
}

.sort-caret.open {
  transform: rotate(180deg);
}

.sort-menu {
  position: absolute;
  top: calc(100% + 8px);
  right: 0;
  min-width: 220px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  box-shadow: var(--shadow);
  padding: 6px;
  display: flex;
  flex-direction: column;
  z-index: 12;
}

.sort-option {
  justify-content: flex-start;
  min-height: 36px;
  border: 1px solid transparent;
  background: transparent;
  color: var(--text);
}

.sort-option.active {
  border-color: var(--primary);
  background: color-mix(in srgb, var(--primary) 12%, transparent);
  color: var(--primary);
}

.grid {
  display: grid;
  grid-template-columns: repeat(var(--grid-columns), minmax(0, 1fr));
  gap: var(--grid-gap, 16px);
}

.card {
  background: var(--surface);
  border: 1px solid var(--border);
  color: var(--text);
  min-height: var(--card-height, 320px);
  display: flex;
  flex-direction: column;
  overflow: hidden;
  border-radius: 14px;
  box-shadow: var(--shadow);
}

.card.layout-media-left {
  flex-direction: row;
}

.card.layout-media-left .media-wrap {
  width: 40%;
  min-width: 120px;
}

.card.layout-media-left .card-body {
  flex: 1;
}

.card.layout-compact {
  min-height: calc(var(--card-height, 320px) - 40px);
}

.card-link {
  text-decoration: none;
  color: inherit;
}

.media-wrap {
  display: block;
}

.card-image {
  width: 100%;
  height: 170px;
  object-fit: cover;
  border-bottom: 1px solid var(--border);
}

.card.layout-media-left .card-image {
  height: 100%;
  min-height: 150px;
  border-bottom: none;
  border-right: 1px solid var(--border);
}

.card-placeholder {
  width: 100%;
  height: 170px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--surface) 62%, var(--border));
  color: var(--muted);
}

.card-body {
  display: flex;
  flex-direction: column;
  gap: 8px;
  padding: 12px;
}

.title {
  margin: 0;
  font-size: 18px;
}

.short-description {
  margin: 0;
  color: var(--muted);
}

.price {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-weight: 700;
}

.price .old {
  text-decoration: line-through;
  color: var(--muted);
  font-weight: 500;
}

.price .new {
  color: var(--primary);
}

.badge {
  display: inline-flex;
  align-self: flex-start;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--primary-soft);
  color: var(--primary-soft-contrast);
  font-size: 12px;
}

.rating-summary {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
  font-size: 13px;
}

.rating-empty {
  color: var(--muted);
}

.reviews-count {
  font-size: 13px;
  color: var(--muted);
}

.buy-btn {
  margin-top: auto;
}

.grid-banner {
  grid-column: 1 / -1;
  display: block;
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  box-shadow: var(--shadow);
}

.grid-banner-image {
  width: 100%;
  max-height: 220px;
  object-fit: cover;
  display: block;
}

.pagination {
  display: flex;
  gap: 10px;
  align-items: center;
  flex-wrap: wrap;
}

@media (max-width: 1080px) {
  .layout {
    grid-template-columns: 1fr;
  }

  .categories {
    flex-direction: row;
    flex-wrap: wrap;
  }

  .products-toolbar {
    flex-wrap: wrap;
  }
}

@media (max-width: 900px) {
  .grid {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 620px) {
  .grid {
    grid-template-columns: 1fr;
  }

  .card.layout-media-left {
    flex-direction: column;
  }

  .card.layout-media-left .media-wrap {
    width: 100%;
  }

  .card.layout-media-left .card-image {
    border-right: none;
    border-bottom: 1px solid var(--border);
  }

  .search-row > .btn {
    width: 100%;
  }
}
</style>
