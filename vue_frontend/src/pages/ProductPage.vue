<template>
  <section class="page bg-app text-app">
    <div v-if="catalogStore.loading" class="state-box">Loading...</div>
    <div v-else-if="catalogStore.error" class="state-box error">{{ catalogStore.error }}</div>

    <div v-else-if="product" class="product-wrap">
      <div
        class="product-main"
        :class="[`layout-${productPagePreset.layout_mode}`, `photo-${productPagePreset.photo_mode}`]"
      >
        <div class="media-panel">
          <img
            v-if="product.image_url"
            :src="product.image_url"
            :alt="product.title"
            class="image"
          />
          <div v-else class="placeholder">No image</div>

          <div class="thumbs" :class="`thumbs-${productPagePreset.photo_mode}`">
            <img v-if="product.thumbnail_url || product.image_url" :src="product.thumbnail_url || product.image_url || ''" alt="thumb" class="thumb" />
            <img v-if="product.image_url" :src="product.image_url" alt="thumb" class="thumb" />
          </div>
        </div>

        <div class="details-panel">
          <template v-for="block in visibleProductPageBlocks" :key="`page-${block.type}`">
            <h1 v-if="block.type === 'title'" class="product-title">{{ product.title }}</h1>

            <div v-else-if="block.type === 'price'" class="price">
              <template v-if="hasDiscount(product)">
                <span class="old">{{ product.price }} {{ product.currency }}</span>
                <span class="new">{{ discountedPrice(product) }} {{ product.currency }}</span>
                <span class="badge">-{{ product.discount_percent }}%</span>
              </template>
              <template v-else>
                <span>{{ product.price }} {{ product.currency }}</span>
              </template>
            </div>

            <button
              v-else-if="block.type === 'rating'"
              type="button"
              class="rating-summary-btn"
              :disabled="!hasRatingSummary"
              @click="openAllReviewsModal"
            >
              <template v-if="hasRatingSummary">
                <StarRatingDisplay :rating="ratingSummary.avg_rating" size="16px" />
                <span>{{ ratingSummary.avg_rating?.toFixed(1) }}</span>
              </template>
              <template v-else>
                <span class="rating-summary-empty">—</span>
              </template>
            </button>

            <button
              v-else-if="block.type === 'reviews_count'"
              type="button"
              class="reviews-count-btn"
              :disabled="reviewsTotal === 0"
              @click="openAllReviewsModal"
            >
              {{ reviewsCountText }}
            </button>

            <p v-else-if="block.type === 'short_description'" class="description">
              {{ product.description || "No description" }}
            </p>

            <div v-else-if="block.type === 'buy_button'" class="buy-block">
              <label class="qty">
                Qty
                <select v-model.number="qty">
                  <option v-for="n in 10" :key="`qty-page-${n}`" :value="n">{{ n }}</option>
                </select>
              </label>
              <button class="btn btn-primary" @click="addToCart">Add to cart</button>
            </div>
          </template>
        </div>

        <aside class="buy-panel" :class="`layout-${productCardPreset.layout_mode}`">
          <h2 class="panel-title">Purchase card</h2>
          <template v-for="block in visibleProductCardBlocks" :key="`card-${block.type}`">
            <h3 v-if="block.type === 'title'">{{ product.title }}</h3>

            <div v-else-if="block.type === 'price'" class="price">
              <template v-if="hasDiscount(product)">
                <span class="old">{{ product.price }} {{ product.currency }}</span>
                <span class="new">{{ discountedPrice(product) }} {{ product.currency }}</span>
              </template>
              <template v-else>
                <span>{{ product.price }} {{ product.currency }}</span>
              </template>
            </div>

            <div v-else-if="block.type === 'rating'" class="rating-summary-inline">
              <template v-if="hasRatingSummary">
                <StarRatingDisplay :rating="ratingSummary.avg_rating" size="14px" />
                <span>{{ ratingSummary.avg_rating?.toFixed(1) }}</span>
              </template>
              <template v-else>
                <span class="rating-summary-empty">—</span>
              </template>
            </div>

            <div v-else-if="block.type === 'reviews_count'" class="reviews-count-inline">
              {{ reviewsCountText }}
            </div>

            <p v-else-if="block.type === 'short_description'" class="description compact">
              {{ shortDescription }}
            </p>

            <div v-else-if="block.type === 'buy_button'" class="buy-block compact">
              <label class="qty compact">
                Qty
                <select v-model.number="qty">
                  <option v-for="n in 10" :key="`qty-card-${n}`" :value="n">{{ n }}</option>
                </select>
              </label>
              <button class="btn btn-primary" @click="addToCart">Add to cart</button>
            </div>
          </template>
        </aside>
      </div>

      <section class="reviews-section">
        <div class="reviews-header">
          <h2>Reviews ({{ reviewsTotal }})</h2>
          <button
            type="button"
            class="btn btn-outline"
            :disabled="reviewsTotal === 0"
            @click="openAllReviewsModal"
          >
            All reviews
          </button>
        </div>

        <div v-if="reviewsLoading" class="state-box">Loading reviews...</div>
        <div v-else-if="reviewsError" class="state-box error">{{ reviewsError }}</div>
        <div v-else-if="latestReviews.length === 0" class="state-box">No reviews yet.</div>
        <ul v-else class="reviews-list">
          <li v-for="review in latestReviews" :key="review.id" class="review-card">
            <div class="review-top">
              <span class="review-author">{{ review.author_display_name }}</span>
              <span class="review-stars">{{ starsText(review.rating) }}</span>
            </div>
            <p v-if="review.pros" class="review-text"><strong>Pros:</strong> {{ review.pros }}</p>
            <p v-if="review.cons" class="review-text"><strong>Cons:</strong> {{ review.cons }}</p>
            <p v-if="review.comment" class="review-text"><strong>Comment:</strong> {{ review.comment }}</p>
            <p class="review-date">{{ formatDate(review.created_at) }}</p>
          </li>
        </ul>
      </section>
    </div>

    <div v-if="showAllReviews && product" class="modal" @click.self="closeAllReviewsModal">
      <div class="modal-card">
        <div class="modal-header">
          <h3>All reviews</h3>
          <button type="button" class="btn btn-neutral close-btn" @click="closeAllReviewsModal">
            Close
          </button>
        </div>

        <div class="filters">
          <label>
            Rating
            <select v-model="ratingFilter">
              <option value="">All</option>
              <option value="4">4★+</option>
              <option value="3">3★+</option>
              <option value="2">2★+</option>
              <option value="1">1★+</option>
            </select>
          </label>

          <label>
            Sort
            <select v-model="sortFilter">
              <option value="created_desc">Date: new to old</option>
              <option value="created_asc">Date: old to new</option>
              <option value="rating_desc">Rating: high to low</option>
              <option value="rating_asc">Rating: low to high</option>
            </select>
          </label>
        </div>

        <div v-if="allReviewsLoading" class="state-box">Loading reviews...</div>
        <div v-else-if="allReviewsError" class="state-box error">{{ allReviewsError }}</div>
        <div v-else-if="allReviews.length === 0" class="state-box">No reviews for selected filters.</div>
        <ul v-else class="reviews-list">
          <li v-for="review in allReviews" :key="review.id" class="review-card">
            <div class="review-top">
              <span class="review-author">{{ review.author_display_name }}</span>
              <span class="review-stars">{{ starsText(review.rating) }}</span>
            </div>
            <p v-if="review.pros" class="review-text"><strong>Pros:</strong> {{ review.pros }}</p>
            <p v-if="review.cons" class="review-text"><strong>Cons:</strong> {{ review.cons }}</p>
            <p v-if="review.comment" class="review-text"><strong>Comment:</strong> {{ review.comment }}</p>
            <p class="review-date">{{ formatDate(review.created_at) }}</p>
          </li>
        </ul>

        <div class="pagination">
          <button
            type="button"
            class="btn btn-neutral"
            :disabled="allPage <= 1 || allReviewsLoading"
            @click="goToPage(allPage - 1)"
          >
            Prev
          </button>
          <span>Page {{ allPage }} / {{ totalPages }}</span>
          <button
            type="button"
            class="btn btn-neutral"
            :disabled="allPage >= totalPages || allReviewsLoading"
            @click="goToPage(allPage + 1)"
          >
            Next
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, onUnmounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import {
  getProductReviews,
  getReviewsSummary,
  trackProductView,
  type ReviewRatingSummary
} from "../api/public";
import StarRatingDisplay from "../components/StarRatingDisplay.vue";
import { useAppearanceStore } from "../stores/appearance";
import { useCartStore } from "../stores/cart";
import { useCatalogStore, type Product } from "../stores/catalog";
import { visibleBlocks } from "../utils/appearance";

type Review = {
  id: number;
  rating: number;
  pros: string;
  cons: string;
  comment: string;
  author_display_name: string;
  created_at: string;
};

const route = useRoute();
const catalogStore = useCatalogStore();
const cartStore = useCartStore();
const appearanceStore = useAppearanceStore();

const product = ref<Product | null>(null);
const qty = ref(1);

const latestReviews = ref<Review[]>([]);
const reviewsTotal = ref(0);
const reviewsLoading = ref(false);
const reviewsError = ref<string | null>(null);
const ratingSummary = ref<ReviewRatingSummary>({ avg_rating: null, reviews_count: 0 });

const showAllReviews = ref(false);
const allReviews = ref<Review[]>([]);
const allReviewsLoading = ref(false);
const allReviewsError = ref<string | null>(null);
const allPage = ref(1);
const allPageSize = ref(10);
const allTotal = ref(0);
const ratingFilter = ref("");
const sortFilter = ref<"created_desc" | "created_asc" | "rating_desc" | "rating_asc">("created_desc");

const productPagePreset = computed(() => appearanceStore.productPagePresetConfig);
const productCardPreset = computed(() => appearanceStore.productCardPresetConfig);

const visibleProductPageBlocks = computed(() => visibleBlocks(productPagePreset.value));
const visibleProductCardBlocks = computed(() => visibleBlocks(productCardPreset.value));

const totalPages = computed(() => {
  const pages = Math.ceil(allTotal.value / allPageSize.value);
  return pages > 0 ? pages : 1;
});

const hasRatingSummary = computed(
  () => ratingSummary.value.reviews_count > 0 && ratingSummary.value.avg_rating !== null
);

const reviewsCountText = computed(() => {
  if (reviewsTotal.value <= 0) {
    return "No reviews";
  }
  return `${reviewsTotal.value} review${reviewsTotal.value === 1 ? "" : "s"}`;
});

const shortDescription = computed(() => {
  const text = product.value?.description || "";
  if (!text) {
    return "No description";
  }
  if (text.length <= 140) {
    return text;
  }
  return `${text.slice(0, 137)}...`;
});

const addToCart = () => {
  if (!product.value?.id) {
    return;
  }
  cartStore.addToCart(product.value.id, qty.value);
};

const hasDiscount = (item: Product) => {
  const discount = Number(item.discount_percent || 0);
  return discount > 0;
};

const discountedPrice = (item: Product) => {
  if (item.discounted_price) {
    return item.discounted_price;
  }
  const price = Number(item.price || 0);
  const discount = Number(item.discount_percent || 0);
  return (price * (1 - discount / 100)).toFixed(2);
};

const starsText = (rating: number) => "★".repeat(rating) + "☆".repeat(5 - rating);

const formatDate = (value: string) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};

const fetchRatingSummary = async () => {
  if (!product.value?.id) {
    ratingSummary.value = { avg_rating: null, reviews_count: 0 };
    reviewsTotal.value = 0;
    return;
  }

  try {
    const response = await getReviewsSummary([product.value.id]);
    ratingSummary.value =
      response.data?.results?.[product.value.id] || { avg_rating: null, reviews_count: 0 };
    reviewsTotal.value = ratingSummary.value.reviews_count;
  } catch {
    ratingSummary.value = { avg_rating: null, reviews_count: 0 };
    reviewsTotal.value = 0;
  }
};

const fetchLatestReviews = async () => {
  if (!product.value?.id) {
    latestReviews.value = [];
    return;
  }

  reviewsLoading.value = true;
  reviewsError.value = null;
  try {
    const response = await getProductReviews(product.value.id, {
      limit: 3,
      sort: "created_desc"
    });
    latestReviews.value = response.data?.results || [];
    if (ratingSummary.value.reviews_count <= 0) {
      reviewsTotal.value = Number(response.data?.pagination?.total || 0);
    }
  } catch (err: any) {
    reviewsError.value = err?.response?.data?.detail || "Failed to load reviews.";
    latestReviews.value = [];
    if (ratingSummary.value.reviews_count <= 0) {
      reviewsTotal.value = 0;
    }
  } finally {
    reviewsLoading.value = false;
  }
};

const fetchAllReviews = async () => {
  if (!product.value?.id) {
    allReviews.value = [];
    allTotal.value = 0;
    return;
  }

  allReviewsLoading.value = true;
  allReviewsError.value = null;
  try {
    const response = await getProductReviews(product.value.id, {
      page: allPage.value,
      page_size: allPageSize.value,
      rating_gte: ratingFilter.value ? Number(ratingFilter.value) : undefined,
      sort: sortFilter.value
    });
    allReviews.value = response.data?.results || [];
    allTotal.value = Number(response.data?.pagination?.total || 0);
  } catch (err: any) {
    allReviewsError.value = err?.response?.data?.detail || "Failed to load reviews.";
    allReviews.value = [];
    allTotal.value = 0;
  } finally {
    allReviewsLoading.value = false;
  }
};

const openAllReviewsModal = async () => {
  showAllReviews.value = true;
  allPage.value = 1;
  await fetchAllReviews();
};

const closeAllReviewsModal = () => {
  showAllReviews.value = false;
};

const goToPage = async (page: number) => {
  if (page < 1 || page > totalPages.value) {
    return;
  }
  allPage.value = page;
  await fetchAllReviews();
};

watch([ratingFilter, sortFilter], async () => {
  if (!showAllReviews.value) {
    return;
  }
  allPage.value = 1;
  await fetchAllReviews();
});

const onReviewSubmitted = async (event: Event) => {
  const payload = (event as CustomEvent<{ productId?: string }>).detail;
  if (!payload?.productId || payload.productId !== product.value?.id) {
    return;
  }
  await fetchRatingSummary();
  await fetchLatestReviews();
  if (showAllReviews.value) {
    allPage.value = 1;
    await fetchAllReviews();
  }
};

onMounted(async () => {
  window.addEventListener("review-submitted", onReviewSubmitted as EventListener);
  void appearanceStore.loadPublishedAppearance();
  product.value = await catalogStore.fetchProductBySlug(String(route.params.slug || ""));
  if (product.value?.id) {
    void trackProductView(product.value.id).catch(() => undefined);
  }
  await fetchRatingSummary();
  await fetchLatestReviews();
});

onUnmounted(() => {
  window.removeEventListener("review-submitted", onReviewSubmitted as EventListener);
});
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
}

.product-wrap {
  display: flex;
  flex-direction: column;
  gap: 22px;
}

.product-main {
  display: grid;
  grid-template-columns: 1.2fr 1fr 320px;
  gap: 16px;
  align-items: start;
}

.product-main.layout-media-top {
  grid-template-columns: 1fr;
}

.product-main.layout-compact {
  grid-template-columns: 1fr 300px;
}

.media-panel,
.details-panel,
.buy-panel {
  border: 1px solid var(--border);
  background: var(--surface);
  border-radius: 12px;
  padding: 14px;
  box-shadow: var(--shadow);
}

.product-main.layout-media-top .buy-panel {
  max-width: 420px;
}

.image {
  width: 100%;
  max-height: 480px;
  object-fit: cover;
  border-radius: 10px;
}

.placeholder {
  width: 100%;
  min-height: 260px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: color-mix(in srgb, var(--surface) 65%, var(--border));
  color: var(--muted);
  border-radius: 10px;
}

.thumbs {
  display: flex;
  gap: 8px;
  margin-top: 10px;
}

.thumbs-thumbnails_right {
  flex-direction: column;
}

.thumbs-thumbnails_bottom,
.thumbs-hover_carousel {
  flex-direction: row;
}

.thumb {
  width: 74px;
  height: 74px;
  object-fit: cover;
  border: 1px solid var(--border);
  border-radius: 6px;
}

.product-title {
  margin: 0;
}

.price {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-weight: 600;
}

.old {
  text-decoration: line-through;
  color: var(--muted);
  font-weight: 400;
}

.new {
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

.rating-summary-btn,
.reviews-count-btn {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  min-height: 0;
  padding: 0;
  border: none;
  background: transparent;
  color: var(--muted);
}

.reviews-count-btn {
  text-decoration: underline;
  text-underline-offset: 2px;
}

.rating-summary-empty {
  color: var(--muted);
}

.description {
  margin: 0;
  color: var(--muted);
  line-height: 1.4;
}

.description.compact {
  font-size: 14px;
}

.buy-block {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.qty {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.qty.compact {
  font-size: 14px;
}

.panel-title {
  margin: 0 0 10px;
  font-size: 16px;
  color: var(--muted);
}

.rating-summary-inline,
.reviews-count-inline {
  display: inline-flex;
  align-items: center;
  gap: 6px;
  color: var(--muted);
}

.reviews-section {
  border: 1px solid var(--border);
  background: var(--surface);
  border-radius: 12px;
  padding: 16px;
  box-shadow: var(--shadow);
}

.reviews-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  margin-bottom: 12px;
}

.reviews-list {
  list-style: none;
  margin: 0;
  padding: 0;
  display: grid;
  gap: 10px;
}

.review-card {
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 10px;
  background: color-mix(in srgb, var(--surface) 96%, var(--primary) 4%);
}

.review-top {
  display: flex;
  justify-content: space-between;
  gap: 10px;
  margin-bottom: 4px;
}

.review-author {
  font-weight: 600;
}

.review-stars {
  color: #f2a100;
}

.review-text {
  margin: 4px 0;
}

.review-date {
  margin: 6px 0 0;
  font-size: 12px;
  color: var(--muted);
}

.modal {
  position: fixed;
  inset: 0;
  background: color-mix(in srgb, var(--text) 45%, transparent);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 18px;
  z-index: 50;
}

.modal-card {
  width: min(860px, 100%);
  max-height: 90vh;
  overflow: auto;
  background: var(--surface);
  border: 1px solid var(--border);
  border-radius: 12px;
  padding: 14px;
}

.modal-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 12px;
  margin-bottom: 12px;
}

.close-btn {
  min-width: 90px;
}

.filters {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
  margin-bottom: 12px;
}

.filters label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.pagination {
  display: flex;
  align-items: center;
  gap: 10px;
  margin-top: 12px;
}

@media (max-width: 1180px) {
  .product-main {
    grid-template-columns: 1fr;
  }
}
</style>
