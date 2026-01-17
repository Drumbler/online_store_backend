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
          <div>Total: {{ order.total }}</div>
          <div>Created: {{ order.created_at }}</div>
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
        <div>Total: {{ lookupResult.total_price }} {{ lookupResult.currency }}</div>
        <div>Created: {{ lookupResult.created_at }}</div>
        <ul v-if="lookupResult.items?.length" class="items">
          <li v-for="(item, index) in lookupResult.items" :key="index">
            {{ item.title_snapshot }} × {{ item.quantity }} @ {{ item.unit_price_snapshot }}
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
