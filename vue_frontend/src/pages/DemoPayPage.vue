<template>
  <section class="page bg-app text-app">
    <h1>Demo payment</h1>

    <p v-if="error" class="state-box error">{{ error }}</p>

    <div v-if="paid" class="state-box success">
      Payment completed.
      <RouterLink :to="orderLink">Open order status</RouterLink>
    </div>

    <div v-else class="card surface-card">
      <p>This is a local demo payment screen.</p>
      <p>External ID: <strong>{{ externalId || "-" }}</strong></p>

      <div class="actions">
        <button type="button" class="btn btn-primary" :disabled="submitting || !externalId" @click="paySuccess">
          Pay (success)
        </button>
        <button type="button" class="btn btn-outline" :disabled="submitting || !externalId" @click="payFail">
          Pay (fail)
        </button>
      </div>

      <button v-if="failed" type="button" class="retry btn btn-neutral" @click="goToRetry">Retry payment</button>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { postPaymentWebhook } from "../api/public";

const route = useRoute();
const router = useRouter();

const submitting = ref(false);
const paid = ref(false);
const failed = ref(false);
const error = ref<string | null>(null);

const providerId = computed(() => String(route.query.provider_id || "demo"));
const externalId = computed(() => String(route.query.external_id || ""));
const orderNumber = computed(() => String(route.query.order_number || ""));

const isLoggedIn = computed(() => Boolean(localStorage.getItem("authToken")));

const orderLink = computed(() => {
  if (isLoggedIn.value) {
    return "/orders";
  }
  const query = new URLSearchParams();
  if (orderNumber.value) {
    query.set("order_number", orderNumber.value);
  }
  const queryString = query.toString();
  return queryString ? `/orders/find?${queryString}` : "/orders/find";
});

const sendWebhook = async (resultStatus: "succeeded" | "failed") => {
  if (!externalId.value) {
    error.value = "external_id is required.";
    return;
  }

  submitting.value = true;
  error.value = null;
  try {
    await postPaymentWebhook(providerId.value, {
      external_id: externalId.value,
      status: resultStatus
    });

    if (resultStatus === "succeeded") {
      paid.value = true;
      failed.value = false;
      await router.push(orderLink.value);
      return;
    }

    failed.value = true;
    paid.value = false;
    error.value = "Payment failed. You can retry.";
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to process payment webhook.";
  } finally {
    submitting.value = false;
  }
};

const paySuccess = async () => {
  await sendWebhook("succeeded");
};

const payFail = async () => {
  await sendWebhook("failed");
};

const goToRetry = async () => {
  const query = new URLSearchParams();
  if (orderNumber.value) {
    query.set("order_number", orderNumber.value);
  }
  const queryString = query.toString();
  await router.push(queryString ? `/pay?${queryString}` : "/pay");
};
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.card {
  max-width: 480px;
  padding: 12px;
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.retry {
  width: fit-content;
}
</style>
