<template>
  <section class="page bg-app text-app">
    <div v-if="catalogStore.loading" class="state-box">Загрузка...</div>
    <div v-else-if="catalogStore.error" class="state-box error">{{ catalogStore.error }}</div>

    <div v-else-if="product" class="product-wrap">
      <div
        class="product-main"
        :class="[layoutClass, photoClass]"
      >
        <div
          class="media-panel"
          :class="mediaModeClass"
          @mouseenter="startHoverCarousel"
          @mouseleave="stopHoverCarousel"
        >
          <div class="image-stage">
            <img
              v-if="activeImageUrl"
              :src="activeImageUrl"
              :alt="product.title"
              class="image"
            />
            <div v-else class="placeholder">Нет изображения</div>
          </div>

          <div v-if="thumbnailItems.length" class="thumbs" :class="thumbsModeClass">
            <button
              v-for="thumb in thumbnailItems"
              :key="`thumb-${thumb.index}-${thumb.url}`"
              type="button"
              class="thumb-btn"
              @click="setActiveImage(thumb.index)"
            >
              <img :src="thumb.url" alt="Миниатюра товара" class="thumb" />
            </button>
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
              {{ product.description || "Нет описания" }}
            </p>

            <div v-else-if="block.type === 'buy_button'" class="buy-block">
              <label class="qty">
                Количество
                <select v-model.number="qty">
                  <option v-for="n in 10" :key="`qty-page-${n}`" :value="n">{{ n }}</option>
                </select>
              </label>
              <button class="btn btn-primary" @click="addToCart">Добавить в корзину</button>
            </div>
          </template>
        </div>
      </div>

      <section class="reviews-section">
        <div class="reviews-header">
          <h2>Отзывы ({{ reviewsTotal }})</h2>
          <button
            type="button"
            class="btn btn-outline"
            :disabled="reviewsTotal === 0"
            @click="openAllReviewsModal"
          >
            Все отзывы
          </button>
        </div>

        <div v-if="reviewsLoading" class="state-box">Загрузка отзывов...</div>
        <div v-else-if="reviewsError" class="state-box error">{{ reviewsError }}</div>
        <div v-else-if="latestReviews.length === 0" class="state-box">Отзывов пока нет.</div>
        <ul v-else class="reviews-list">
          <li v-for="review in latestReviews" :key="review.id" class="review-card">
            <div class="review-top">
              <span class="review-author">{{ review.author_display_name }}</span>
              <span class="review-stars">{{ starsText(review.rating) }}</span>
            </div>
            <p v-if="review.pros" class="review-text"><strong>Плюсы:</strong> {{ review.pros }}</p>
            <p v-if="review.cons" class="review-text"><strong>Минусы:</strong> {{ review.cons }}</p>
            <p v-if="review.comment" class="review-text"><strong>Комментарий:</strong> {{ review.comment }}</p>
            <p class="review-date">{{ formatDate(review.created_at) }}</p>
          </li>
        </ul>
      </section>
    </div>

    <div v-if="showAllReviews && product" class="modal" @click.self="closeAllReviewsModal">
      <div class="modal-card">
        <div class="modal-header">
          <h3>Все отзывы</h3>
          <button type="button" class="btn btn-neutral close-btn" @click="closeAllReviewsModal">
            Закрыть
          </button>
        </div>

        <div class="filters">
          <label>
            Рейтинг
            <select v-model="ratingFilter">
              <option value="">Все</option>
              <option value="4">4★+</option>
              <option value="3">3★+</option>
              <option value="2">2★+</option>
              <option value="1">1★+</option>
            </select>
          </label>

          <label>
            Сортировка
            <select v-model="sortFilter">
              <option value="created_desc">Дата: новые сначала</option>
              <option value="created_asc">Дата: старые сначала</option>
              <option value="rating_desc">Рейтинг: высокий к низкому</option>
              <option value="rating_asc">Рейтинг: низкий к высокому</option>
            </select>
          </label>
        </div>

        <div v-if="allReviewsLoading" class="state-box">Загрузка отзывов...</div>
        <div v-else-if="allReviewsError" class="state-box error">{{ allReviewsError }}</div>
        <div v-else-if="allReviews.length === 0" class="state-box">Нет отзывов для выбранных фильтров.</div>
        <ul v-else class="reviews-list">
          <li v-for="review in allReviews" :key="review.id" class="review-card">
            <div class="review-top">
              <span class="review-author">{{ review.author_display_name }}</span>
              <span class="review-stars">{{ starsText(review.rating) }}</span>
            </div>
            <p v-if="review.pros" class="review-text"><strong>Плюсы:</strong> {{ review.pros }}</p>
            <p v-if="review.cons" class="review-text"><strong>Минусы:</strong> {{ review.cons }}</p>
            <p v-if="review.comment" class="review-text"><strong>Комментарий:</strong> {{ review.comment }}</p>
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
            Назад
          </button>
          <span>Страница {{ allPage }} / {{ totalPages }}</span>
          <button
            type="button"
            class="btn btn-neutral"
            :disabled="allPage >= totalPages || allReviewsLoading"
            @click="goToPage(allPage + 1)"
          >
            Вперёд
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
/** Логика страницы и обработчики UI состояния. */
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
const activeImageIndex = ref(0);
let hoverCarouselTimer: ReturnType<typeof setInterval> | null = null;

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
const visibleProductPageBlocks = computed(() => visibleBlocks(productPagePreset.value));

const normalizeModeToken = (value: unknown, fallback: string) => {
  const token = String(value || "")
    .trim()
    .replace(/_/g, "-");
  return token || fallback;
};

const layoutClass = computed(() => `layout-${normalizeModeToken(productPagePreset.value.layout_mode, "media-left")}`);
const photoClass = computed(() => `photo-${normalizeModeToken(productPagePreset.value.photo_mode, "thumbnails-bottom")}`);
const mediaModeClass = computed(() =>
  `media-${normalizeModeToken(productPagePreset.value.photo_mode, "thumbnails-bottom")}`
);
const thumbsModeClass = computed(() =>
  `thumbs-${normalizeModeToken(productPagePreset.value.photo_mode, "thumbnails-bottom")}`
);

const appendImageUrls = (source: unknown, bucket: Set<string>) => {
  if (!source) {
    return;
  }
  if (typeof source === "string") {
    const url = source.trim();
    if (url) {
      bucket.add(url);
    }
    return;
  }
  if (Array.isArray(source)) {
    source.forEach((entry) => appendImageUrls(entry, bucket));
    return;
  }
  if (typeof source !== "object") {
    return;
  }
  const value = source as Record<string, unknown>;
  appendImageUrls(value.url, bucket);
  appendImageUrls(value.src, bucket);
  appendImageUrls(value.image_url, bucket);
  appendImageUrls(value.full, bucket);
  appendImageUrls(value.original, bucket);
  appendImageUrls(value.large, bucket);
  appendImageUrls(value.medium, bucket);
  appendImageUrls(value.small, bucket);
  appendImageUrls(value.thumbnail, bucket);
  appendImageUrls(value.data, bucket);
  appendImageUrls(value.attributes, bucket);
};

const collectProductImages = (item: Product | null) => {
  if (!item) {
    return [] as string[];
  }

  const payload = item as unknown as Record<string, unknown>;
  const urls = new Set<string>();

  appendImageUrls(payload.image_url, urls);

  const galleryFields = [
    "gallery_urls",
    "images",
    "image_urls",
    "gallery",
    "gallery_images",
    "image_gallery",
    "photos",
    "media",
    "additional_images"
  ];

  galleryFields.forEach((field) => appendImageUrls(payload[field], urls));

  if (urls.size === 0) {
    appendImageUrls(payload.thumbnail_url, urls);
  }

  return Array.from(urls);
};

const productImages = computed(() => {
  return collectProductImages(product.value);
});
const activeImageUrl = computed(() => {
  if (productImages.value.length === 0) {
    return "";
  }
  const safeIndex = Math.min(activeImageIndex.value, productImages.value.length - 1);
  return productImages.value[safeIndex] || productImages.value[0];
});
const thumbnailItems = computed(() =>
  productImages.value
    .map((url, index) => ({ url, index }))
    .filter((item) => item.url && item.url !== activeImageUrl.value)
);

const totalPages = computed(() => {
  const pages = Math.ceil(allTotal.value / allPageSize.value);
  return pages > 0 ? pages : 1;
});

const hasRatingSummary = computed(
  () => ratingSummary.value.reviews_count > 0 && ratingSummary.value.avg_rating !== null
);

const reviewsCountText = computed(() => {
  const count = reviewsTotal.value;
  if (count <= 0) {
    return "Нет отзывов";
  }
  const mod10 = count % 10;
  const mod100 = count % 100;
  if (mod10 === 1 && mod100 !== 11) {
    return `${count} отзыв`;
  }
  if (mod10 >= 2 && mod10 <= 4 && (mod100 < 12 || mod100 > 14)) {
    return `${count} отзыва`;
  }
  return `${count} отзывов`;
});

const addToCart = () => {
  if (!product.value?.id) {
    return;
  }
  cartStore.addToCart(product.value.id, qty.value);
};

const setActiveImage = (nextIndex: number) => {
  if (nextIndex < 0 || nextIndex >= productImages.value.length) {
    return;
  }
  activeImageIndex.value = nextIndex;
};

const stopHoverCarousel = () => {
  if (!hoverCarouselTimer) {
    return;
  }
  clearInterval(hoverCarouselTimer);
  hoverCarouselTimer = null;
};

const startHoverCarousel = () => {
  if (productPagePreset.value.photo_mode !== "hover_carousel") {
    return;
  }
  if (productImages.value.length <= 1) {
    return;
  }
  stopHoverCarousel();
  hoverCarouselTimer = setInterval(() => {
    activeImageIndex.value = (activeImageIndex.value + 1) % productImages.value.length;
  }, 1200);
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
    reviewsError.value = err?.response?.data?.detail || "Не удалось загрузить отзывы.";
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
    allReviewsError.value = err?.response?.data?.detail || "Не удалось загрузить отзывы.";
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

watch(
  () => product.value?.id,
  () => {
    activeImageIndex.value = 0;
    stopHoverCarousel();
  }
);

watch(
  () => productPagePreset.value.photo_mode,
  () => {
    stopHoverCarousel();
  }
);

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
  stopHoverCarousel();
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
  grid-template-columns: minmax(360px, 1.15fr) minmax(320px, 1fr);
  gap: 16px;
  align-items: start;
}

.product-main.layout-media-top,
.product-main.layout-media_top {
  grid-template-columns: 1fr;
}

.product-main.layout-media-left,
.product-main.layout-media_left {
  grid-template-columns: minmax(360px, 1.15fr) minmax(320px, 1fr);
}

.product-main.layout-compact {
  grid-template-columns: minmax(240px, 320px) minmax(320px, 1fr);
}

.media-panel,
.details-panel {
  border: 1px solid var(--border);
  background: var(--surface);
  border-radius: 12px;
  padding: 14px;
  box-shadow: var(--shadow);
}

.details-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.media-panel {
  display: flex;
  flex-direction: column;
  gap: 10px;
  min-width: 0;
}

.image-stage {
  min-width: 0;
}

.media-panel.media-thumbnails-right,
.media-panel.media-thumbnails_right {
  display: grid;
  grid-template-columns: minmax(0, 1fr) auto;
  align-items: start;
}

.media-panel.media-thumbnails-right .thumbs,
.media-panel.media-thumbnails_right .thumbs {
  margin-top: 0;
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

.thumbs-thumbnails-right,
.thumbs-thumbnails_right {
  flex-direction: column;
  max-height: 480px;
  overflow: auto;
}

.thumbs-thumbnails-bottom,
.thumbs-thumbnails_bottom,
.thumbs-hover-carousel,
.thumbs-hover_carousel {
  flex-direction: row;
}

.thumbs-hover-carousel,
.thumbs-hover_carousel {
  display: none;
}

.thumb-btn {
  border: none;
  background: transparent;
  padding: 0;
  min-height: 0;
  line-height: 0;
  cursor: pointer;
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

.rating-summary-btn + .reviews-count-btn {
  margin-left: 8px;
}

.reviews-count-btn + .rating-summary-btn {
  margin-left: 8px;
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

@media (max-width: 840px) {
  .product-main {
    grid-template-columns: 1fr;
  }

  .media-panel.media-thumbnails-right,
  .media-panel.media-thumbnails_right {
    grid-template-columns: 1fr;
  }

  .thumbs-thumbnails-right,
  .thumbs-thumbnails_right {
    flex-direction: row;
    max-height: none;
  }
}
</style>
