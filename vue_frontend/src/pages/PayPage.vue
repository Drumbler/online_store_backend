<template>
  <section class="page bg-app text-app">
    <h1>Choose payment method</h1>

    <p v-if="error" class="state-box error">{{ error }}</p>

    <div v-if="loading" class="state-box">Loading payment methods...</div>
    <div v-else-if="methods.length === 0" class="state-box">No payment methods available.</div>

    <div v-else class="methods">
      <label v-for="method in methods" :key="method.provider_id" class="method-card surface-card">
        <input v-model="selectedProvider" type="radio" :value="method.provider_id" :disabled="submitting" />
        <div>
          <strong>{{ method.title }}</strong>
          <p>{{ method.is_sandbox ? "Sandbox" : "Production" }}</p>
        </div>
      </label>
    </div>

    <button
      type="button"
      class="btn btn-primary"
      :disabled="submitting || !selectedProvider || methods.length === 0"
      @click="proceed"
    >
      Proceed to payment
    </button>
  </section>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import { createPayment, getCheckoutPaymentMethods } from "../api/public";

type PaymentMethod = {
  provider_id: string;
  title: string;
  is_sandbox: boolean;
};

const route = useRoute();

const methods = ref<PaymentMethod[]>([]);
const selectedProvider = ref("");
const loading = ref(false);
const submitting = ref(false);
const error = ref<string | null>(null);

const orderNumber = ref("");
const orderSecret = ref("");

const loadMethods = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await getCheckoutPaymentMethods();
    methods.value = response.data?.results || [];
    if (methods.value.length > 0) {
      selectedProvider.value = methods.value[0].provider_id;
    }
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to load payment methods.";
  } finally {
    loading.value = false;
  }
};

const proceed = async () => {
  if (!selectedProvider.value || !orderNumber.value) {
    return;
  }
  submitting.value = true;
  error.value = null;
  try {
    const payload: { order_number: string; provider_id: string; order_secret?: string } = {
      order_number: orderNumber.value,
      provider_id: selectedProvider.value
    };
    if (orderSecret.value) {
      payload.order_secret = orderSecret.value;
    }
    const response = await createPayment(payload);
    const paymentUrl = response.data?.payment_url;
    if (!paymentUrl) {
      throw new Error("No payment URL returned.");
    }
    window.location.href = paymentUrl;
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to create payment.";
  } finally {
    submitting.value = false;
  }
};

onMounted(async () => {
  orderNumber.value = String(route.query.order_number || "");
  orderSecret.value = String(route.query.order_secret || "");
  if (!orderNumber.value) {
    error.value = "Order number is required.";
    return;
  }
  await loadMethods();
});
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.methods {
  display: flex;
  flex-direction: column;
  gap: 10px;
  max-width: 520px;
}

.method-card {
  display: flex;
  gap: 10px;
  align-items: flex-start;
  padding: 12px;
}

.method-card p {
  margin: 4px 0 0;
  color: var(--muted);
}
</style>
