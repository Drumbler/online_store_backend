<template>
  <section class="page bg-app text-app">
    <h1>Демо-оплата</h1>

    <p v-if="error" class="state-box error">{{ error }}</p>

    <div v-if="paid" class="state-box success">
      Оплата завершена.
      <RouterLink :to="orderLink">Открыть статус заказа</RouterLink>
    </div>

    <div v-else class="card surface-card">
      <p>Это локальный экран демо-оплаты.</p>
      <p>Внешний идентификатор: <strong>{{ externalId || "-" }}</strong></p>

      <div class="actions">
        <button type="button" class="btn btn-primary" :disabled="submitting || !externalId" @click="paySuccess">
          Оплатить (успех)
        </button>
        <button type="button" class="btn btn-outline" :disabled="submitting || !externalId" @click="payFail">
          Оплатить (ошибка)
        </button>
      </div>

      <button v-if="failed" type="button" class="retry btn btn-neutral" @click="goToRetry">Повторить оплату</button>
    </div>
  </section>
</template>

<script setup lang="ts">
/** Логика страницы и обработчики UI состояния. */
import { computed, ref } from "vue";
import { useRoute, useRouter } from "vue-router";

import { postPaymentWebhook } from "../api/public";
import { useAuthStore } from "../stores/auth";

const route = useRoute();
const router = useRouter();
const authStore = useAuthStore();

const submitting = ref(false);
const paid = ref(false);
const failed = ref(false);
const error = ref<string | null>(null);

const providerId = computed(() => String(route.query.provider_id || "demo"));
const externalId = computed(() => String(route.query.external_id || ""));
const orderNumber = computed(() => String(route.query.order_number || ""));

const isLoggedIn = computed(() => Boolean(authStore.token));

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
    error.value = "Требуется внешний идентификатор оплаты.";
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
    error.value = "Оплата не прошла. Вы можете повторить попытку.";
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Не удалось обработать webhook оплаты.";
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
