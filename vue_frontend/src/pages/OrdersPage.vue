<template>
  <section class="page bg-app text-app">
    <p v-if="toast" class="state-box success">{{ toast }}</p>

    <h1 v-if="isLoggedIn">My Orders</h1>
    <h1 v-else>Order Lookup</h1>

    <section v-if="eligibleProducts.length" class="reviews-strip surface-card">
      <div class="strip-header">
        <h2>Rate your recent purchases</h2>
      </div>
      <div class="eligible-track">
        <article v-for="item in eligibleProducts" :key="item.review_token" class="eligible-card">
          <img v-if="item.image_url" :src="item.image_url" :alt="item.title" class="eligible-image" />
          <div v-else class="eligible-placeholder">No image</div>
          <div class="eligible-content">
            <p class="eligible-title">{{ item.title || item.product_id }}</p>
            <button type="button" class="btn btn-primary" @click="openReviewModal(item)">Leave review</button>
          </div>
        </article>
      </div>
    </section>

    <div v-if="isLoggedIn">
      <div v-if="loadingOrders" class="state-box">Loading...</div>
      <div v-else-if="error" class="state-box error">{{ error }}</div>
      <ul v-else-if="orders.length" class="list">
        <li v-for="order in orders" :key="order.id" class="order surface-card">
          <div>Order #{{ order.order_number ?? order.id }}</div>
          <div>
            Status:
            <span class="order-status" :class="statusToneClass(order.status)">
              {{ order.status }}
            </span>
          </div>
          <div>Subtotal: {{ order.subtotal_original }} {{ orderCurrency(order) }}</div>
          <div>Discount: -{{ order.discount_total }} {{ orderCurrency(order) }}</div>
          <div>Shipping: {{ order.shipping_price ?? "0.00" }} {{ orderCurrency(order) }}</div>
          <div>Total: {{ order.total }} {{ orderCurrency(order) }}</div>
          <div>Created: {{ order.created_at }}</div>
          <ul v-if="order.items?.length" class="items">
            <li v-for="item in order.items" :key="item.id" class="item-row">
              <div>{{ item.product_title_snapshot }} x {{ item.quantity }}</div>
              <div class="price">
                <template v-if="Number(item.discount_percent || 0) > 0">
                  <span class="old">{{ item.unit_price_original }}</span>
                  <span class="new">{{ item.unit_price_final }}</span>
                  <span class="badge">-{{ item.discount_percent }}%</span>
                </template>
                <template v-else>
                  <span>{{ item.unit_price_final || item.unit_price_snapshot }}</span>
                </template>
              </div>
              <div>Line total: {{ item.line_total }} {{ orderCurrency(order) }}</div>
            </li>
          </ul>
        </li>
      </ul>
      <p v-else class="state-box">No orders yet.</p>
    </div>

    <div v-else class="lookup">
      <form class="form surface-card" @submit.prevent="submitLookup">
        <label class="field">
          <span>Order number</span>
          <input v-model="lookupNumber" type="text" required />
        </label>
        <label class="field">
          <span>Order secret</span>
          <input v-model="lookupSecret" type="text" required />
        </label>
        <button type="submit" class="btn btn-primary" :disabled="loadingLookup">Find order</button>
      </form>

      <div v-if="loadingLookup" class="state-box">Loading...</div>
      <div v-if="error" class="state-box error">{{ error }}</div>

      <div v-if="lookupResult" class="order surface-card">
        <div>Order #{{ lookupResult.order_number ?? lookupResult.id }}</div>
        <div>
          Status:
          <span class="order-status" :class="statusToneClass(lookupResult.status)">
            {{ lookupResult.status }}
          </span>
        </div>
        <div>Subtotal: {{ lookupResult.subtotal_original }} {{ lookupResult.currency }}</div>
        <div>Discount: -{{ lookupResult.discount_total }} {{ lookupResult.currency }}</div>
        <div>Shipping: {{ lookupResult.shipping_price ?? "0.00" }} {{ lookupResult.currency }}</div>
        <div>Total: {{ lookupResult.total_price }} {{ lookupResult.currency }}</div>
        <div>Created: {{ lookupResult.created_at }}</div>
        <ul v-if="lookupResult.items?.length" class="items">
          <li v-for="(item, index) in lookupResult.items" :key="index" class="item-row">
            <div>{{ item.title_snapshot }} x {{ item.quantity }}</div>
            <div class="price">
              <template v-if="Number(item.discount_percent || 0) > 0">
                <span class="old">{{ item.unit_price_original }}</span>
                <span class="new">{{ item.unit_price_final }}</span>
                <span class="badge">-{{ item.discount_percent }}%</span>
              </template>
              <template v-else>
                <span>{{ item.unit_price_final || item.unit_price_snapshot }}</span>
              </template>
            </div>
            <div>Line total: {{ item.line_total }} {{ lookupResult.currency }}</div>
          </li>
        </ul>
      </div>
    </div>

    <div v-if="showReviewModal && selectedReviewItem" class="modal" @click.self="closeReviewModal">
      <div class="modal-card surface-card">
        <h3>Leave review</h3>
        <p class="review-product">{{ selectedReviewItem.title || selectedReviewItem.product_id }}</p>

        <div class="stars" @mouseleave="hoverRating = 0">
          <button
            v-for="star in 5"
            :key="star"
            type="button"
            class="star-btn"
            :class="{ active: star <= (hoverRating || reviewRating) }"
            @mouseenter="hoverRating = star"
            @click="reviewRating = star"
          >
            ★
          </button>
        </div>

        <label>
          Pros
          <textarea v-model="reviewPros" rows="3" />
        </label>

        <label>
          Cons
          <textarea v-model="reviewCons" rows="3" />
        </label>

        <label>
          Comment
          <textarea v-model="reviewComment" rows="4" />
        </label>

        <label class="check-row">
          <input v-model="reviewAnonymous" type="checkbox" />
          <span>Leave anonymously</span>
        </label>

        <p v-if="reviewError" class="state-box error">{{ reviewError }}</p>

        <div class="modal-actions">
          <button type="button" class="btn btn-neutral" @click="closeReviewModal">Cancel</button>
          <button type="button" class="btn btn-primary" :disabled="submittingReview" @click="submitReviewForm">
            Submit
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute } from "vue-router";

import { useAuthStore } from "../stores/auth";
import { getUserOrders } from "../api/user";
import { getEligibleReviewProducts, lookupOrder, submitReview } from "../api/public";

type EligibleReviewItem = {
  product_id: string;
  title: string;
  image_url: string | null;
  review_token: string;
};

const authStore = useAuthStore();
const route = useRoute();
const orders = ref<any[]>([]);
const lookupNumber = ref("");
const lookupSecret = ref("");
const lookupResult = ref<any | null>(null);
const eligibleProducts = ref<EligibleReviewItem[]>([]);

const loadingOrders = ref(false);
const loadingLookup = ref(false);
const error = ref<string | null>(null);
const toast = ref<string | null>(null);

const showReviewModal = ref(false);
const selectedReviewItem = ref<EligibleReviewItem | null>(null);
const reviewRating = ref(0);
const hoverRating = ref(0);
const reviewPros = ref("");
const reviewCons = ref("");
const reviewComment = ref("");
const reviewAnonymous = ref(false);
const reviewError = ref<string | null>(null);
const submittingReview = ref(false);

const isLoggedIn = computed(() => Boolean(authStore.token));

const showToast = (message: string) => {
  toast.value = message;
  window.setTimeout(() => {
    if (toast.value === message) {
      toast.value = null;
    }
  }, 3500);
};

const fetchOrders = async () => {
  loadingOrders.value = true;
  error.value = null;
  try {
    const response = await getUserOrders();
    const data = response.data;
    orders.value = data.results || data || [];
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to load orders.";
  } finally {
    loadingOrders.value = false;
  }
};

const fetchEligibleReviews = async () => {
  try {
    const params = isLoggedIn.value
      ? undefined
      : {
          order_number: lookupNumber.value,
          order_secret: lookupSecret.value
        };
    const response = await getEligibleReviewProducts(params);
    eligibleProducts.value = response.data?.results || [];
  } catch {
    eligibleProducts.value = [];
  }
};

const submitLookup = async () => {
  loadingLookup.value = true;
  error.value = null;
  lookupResult.value = null;
  eligibleProducts.value = [];
  try {
    const response = await lookupOrder(lookupNumber.value, lookupSecret.value);
    lookupResult.value = response.data;
    localStorage.setItem("guestOrderNumber", lookupNumber.value);
    localStorage.setItem("guestOrderSecret", lookupSecret.value);
    await fetchEligibleReviews();
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Order not found.";
  } finally {
    loadingLookup.value = false;
  }
};

const openReviewModal = (item: EligibleReviewItem) => {
  selectedReviewItem.value = item;
  reviewRating.value = 0;
  hoverRating.value = 0;
  reviewPros.value = "";
  reviewCons.value = "";
  reviewComment.value = "";
  reviewAnonymous.value = false;
  reviewError.value = null;
  showReviewModal.value = true;
};

const closeReviewModal = () => {
  showReviewModal.value = false;
  selectedReviewItem.value = null;
};

const submitReviewForm = async () => {
  if (!selectedReviewItem.value) {
    return;
  }
  if (reviewRating.value < 1 || reviewRating.value > 5) {
    reviewError.value = "Please choose a rating from 1 to 5.";
    return;
  }

  submittingReview.value = true;
  reviewError.value = null;
  try {
    const reviewedProductId = selectedReviewItem.value.product_id;
    await submitReview({
      review_token: selectedReviewItem.value.review_token,
      rating: reviewRating.value,
      pros: reviewPros.value,
      cons: reviewCons.value,
      comment: reviewComment.value,
      is_anonymous: reviewAnonymous.value
    });
    window.dispatchEvent(
      new CustomEvent("review-submitted", {
        detail: { productId: reviewedProductId }
      })
    );
    eligibleProducts.value = eligibleProducts.value.filter(
      (item) => item.review_token !== selectedReviewItem.value?.review_token
    );
    closeReviewModal();
    showToast("Review submitted.");
  } catch (err: any) {
    reviewError.value = err?.response?.data?.detail || "Failed to submit review.";
  } finally {
    submittingReview.value = false;
  }
};

const orderCurrency = (order: any) => {
  const item = order?.items?.[0];
  return item?.currency_snapshot || "RUB";
};

const statusToneClass = (status?: string) => {
  const normalized = String(status || "").toLowerCase();
  if (/(paid|complete|success|done|delivered)/.test(normalized)) {
    return "status-success";
  }
  if (/(fail|cancel|declin|refund|reject)/.test(normalized)) {
    return "status-danger";
  }
  if (/(pending|new|process|await)/.test(normalized)) {
    return "status-warn";
  }
  return "status-neutral";
};

watch(isLoggedIn, async (value) => {
  orders.value = [];
  lookupResult.value = null;
  eligibleProducts.value = [];
  error.value = null;

  if (value) {
    await fetchOrders();
    await fetchEligibleReviews();
  }
});

onMounted(async () => {
  if (isLoggedIn.value) {
    await fetchOrders();
    await fetchEligibleReviews();
    return;
  }

  const queryNumber = typeof route.query.order_number === "string" ? route.query.order_number : "";
  const querySecret = typeof route.query.order_secret === "string" ? route.query.order_secret : "";
  if (queryNumber && querySecret) {
    lookupNumber.value = queryNumber;
    lookupSecret.value = querySecret;
    await submitLookup();
    return;
  }

  const savedNumber = localStorage.getItem("guestOrderNumber");
  const savedSecret = localStorage.getItem("guestOrderSecret");
  if (savedNumber && savedSecret) {
    lookupNumber.value = savedNumber;
    lookupSecret.value = savedSecret;
  }
});
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.reviews-strip {
  display: flex;
  flex-direction: column;
  gap: 10px;
  padding: 12px;
}

.strip-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
}

.strip-header h2 {
  margin: 0;
  font-size: 20px;
}

.eligible-track {
  display: flex;
  gap: 12px;
  overflow-x: auto;
  padding-bottom: 4px;
}

.eligible-card {
  min-width: 220px;
  max-width: 220px;
  border: 1px solid var(--border);
  border-radius: 12px;
  background: var(--surface);
  overflow: hidden;
}

.eligible-image,
.eligible-placeholder {
  width: 100%;
  height: 140px;
  object-fit: cover;
  border-bottom: 1px solid var(--border);
}

.eligible-placeholder {
  display: flex;
  align-items: center;
  justify-content: center;
  color: var(--muted);
  background: color-mix(in srgb, var(--surface) 80%, var(--border));
}

.eligible-content {
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.eligible-title {
  margin: 0;
}

.list {
  list-style: none;
  padding: 0;
  margin: 0;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.order {
  padding: 12px;
}

.order-status {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  border: 1px solid var(--border);
  font-weight: 600;
  margin-left: 6px;
}

.order-status.status-success {
  border-color: color-mix(in srgb, #2f8f52 45%, var(--border));
  background: color-mix(in srgb, #2f8f52 12%, var(--surface));
  color: color-mix(in srgb, #2f8f52 75%, var(--text));
}

.order-status.status-danger {
  border-color: color-mix(in srgb, #d13b3b 45%, var(--border));
  background: color-mix(in srgb, #d13b3b 12%, var(--surface));
  color: color-mix(in srgb, #d13b3b 78%, var(--text));
}

.order-status.status-warn {
  border-color: color-mix(in srgb, #b87a17 45%, var(--border));
  background: color-mix(in srgb, #b87a17 14%, var(--surface));
  color: color-mix(in srgb, #b87a17 75%, var(--text));
}

.order-status.status-neutral {
  background: color-mix(in srgb, var(--surface) 90%, var(--border));
  color: var(--text);
}

.items {
  list-style: none;
  padding: 0;
  margin: 12px 0 0;
  display: grid;
  gap: 6px;
}

.item-row {
  display: grid;
  gap: 4px;
  border-top: 1px solid var(--border);
  padding-top: 8px;
}

.price {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.old {
  text-decoration: line-through;
  color: var(--muted);
}

.new {
  font-weight: 600;
  color: var(--primary);
}

.badge {
  display: inline-flex;
  width: fit-content;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--primary-soft);
  color: var(--primary-soft-contrast);
  font-size: 12px;
}

.lookup {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 420px;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  padding: 14px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.4);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 20px;
  z-index: 40;
}

.modal-card {
  width: min(620px, 100%);
  max-height: 92vh;
  overflow: auto;
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.review-product {
  margin: 0;
  color: var(--muted);
}

.stars {
  display: flex;
  gap: 6px;
}

.star-btn {
  border: none;
  background: transparent;
  color: color-mix(in srgb, var(--muted) 45%, var(--border));
  font-size: 28px;
  cursor: pointer;
  padding: 0;
  line-height: 1;
}

.star-btn.active {
  color: color-mix(in srgb, #e3a728 80%, var(--text));
}

.check-row {
  display: flex;
  align-items: center;
  gap: 8px;
}

.modal-card label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 8px;
}

@media (max-width: 700px) {
  .eligible-card {
    min-width: 190px;
    max-width: 190px;
  }

  .eligible-image,
  .eligible-placeholder {
    height: 120px;
  }
}
</style>
