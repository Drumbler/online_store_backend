<template>
  <section class="page">
    <h1 v-if="isLoggedIn">My Orders</h1>
    <h1 v-else>Order Lookup</h1>

    <div v-if="loading" class="status">Loading...</div>
    <div v-else-if="error" class="status error">{{ error }}</div>

    <div v-if="isLoggedIn">
      <ul v-if="orders.length" class="list">
        <li v-for="order in orders" :key="order.id" class="order">
          <div>Order #{{ order.order_number ?? order.id }}</div>
          <div>Status: {{ order.status }}</div>
          <div>Subtotal: {{ order.subtotal_original }} {{ orderCurrency(order) }}</div>
          <div>Discount: -{{ order.discount_total }} {{ orderCurrency(order) }}</div>
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
      <p v-else class="status">No orders yet.</p>
    </div>

    <div v-else class="lookup">
      <form class="form" @submit.prevent="submitLookup">
        <label class="field">
          <span>Order number</span>
          <input v-model="lookupNumber" type="text" required />
        </label>
        <button type="submit" :disabled="loading">Find order</button>
      </form>

      <div v-if="lookupResult" class="order">
        <div>Order #{{ lookupResult.order_number ?? lookupResult.id }}</div>
        <div>Status: {{ lookupResult.status }}</div>
        <div>Subtotal: {{ lookupResult.subtotal_original }} {{ lookupResult.currency }}</div>
        <div>Discount: -{{ lookupResult.discount_total }} {{ lookupResult.currency }}</div>
        <div>Total: {{ lookupResult.total_price }} {{ lookupResult.currency }}</div>
        <div>Created: {{ lookupResult.created_at }}</div>
        <ul v-if="lookupResult.items?.length" class="items">
          <li v-for="(item, index) in lookupResult.items" :key="index">
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
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { useAuthStore } from "../stores/auth";
import { getUserOrders } from "../api/user";
import { lookupOrder } from "../api/public";

const authStore = useAuthStore();
const orders = ref<any[]>([]);
const lookupNumber = ref("");
const lookupResult = ref<any | null>(null);
const loading = ref(false);
const error = ref<string | null>(null);

const isLoggedIn = computed(() => Boolean(authStore.token));

const fetchOrders = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await getUserOrders();
    const data = response.data;
    orders.value = data.results || data || [];
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to load orders.";
  } finally {
    loading.value = false;
  }
};

const submitLookup = async () => {
  loading.value = true;
  error.value = null;
  lookupResult.value = null;
  try {
    const response = await lookupOrder(lookupNumber.value);
    lookupResult.value = response.data;
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Order not found.";
  } finally {
    loading.value = false;
  }
};

const orderCurrency = (order: any) => {
  const item = order?.items?.[0];
  return item?.currency_snapshot || "RUB";
};

watch(isLoggedIn, (value) => {
  orders.value = [];
  lookupResult.value = null;
  error.value = null;
  if (value) {
    fetchOrders();
  }
});

onMounted(() => {
  if (isLoggedIn.value) {
    fetchOrders();
  }
});
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
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
  border: 1px solid #e0e0e0;
  background: #fff;
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
  border-top: 1px solid #f0f0f0;
  padding-top: 8px;
}

.price {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.old {
  text-decoration: line-through;
  color: #8a7b68;
}

.new {
  font-weight: 600;
  color: #2f4b2f;
}

.badge {
  display: inline-flex;
  width: fit-content;
  padding: 2px 8px;
  border-radius: 999px;
  background: #efe4cf;
  color: #4b3c2f;
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
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.status {
  padding: 12px;
  background: #fff6d8;
  border: 1px solid #f0dca0;
}

.status.error {
  background: #ffe1e1;
  border-color: #f2b3b3;
}
</style>
