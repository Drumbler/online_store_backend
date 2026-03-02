<template>
  <section class="page bg-app text-app">
    <h1>Выбор способа оплаты</h1>

    <p v-if="error" class="state-box error">{{ error }}</p>

    <div v-if="loading" class="state-box">Загрузка способов оплаты...</div>
    <div v-else-if="methodOptions.length === 0" class="state-box">Нет доступных способов оплаты.</div>

    <div v-else class="methods">
      <label v-for="option in methodOptions" :key="option.option_id" class="method-card surface-card">
        <input v-model="selectedOptionId" type="radio" :value="option.option_id" :disabled="submitting" />
        <div>
          <strong>{{ option.title }}</strong>
          <p>{{ option.description }}</p>
        </div>
      </label>
    </div>

    <div class="actions">
      <button
        type="button"
        class="btn btn-primary"
        :disabled="submitting || !selectedMethod || methodOptions.length === 0"
        @click="proceed"
      >
        Перейти к оплате
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
/** Логика страницы и обработчики UI состояния. */
import { computed, onMounted, ref } from "vue";
import { useRoute } from "vue-router";

import { createPayment, getCheckoutPaymentMethods } from "../api/public";

type PaymentMethod = {
  provider_id: string;
  title: string;
  is_sandbox: boolean;
};

type PaymentOption = {
  option_id: string;
  provider_id: string;
  title: string;
  description: string;
};

const route = useRoute();

const methods = ref<PaymentMethod[]>([]);
const selectedOptionId = ref("");
const loading = ref(false);
const submitting = ref(false);
const error = ref<string | null>(null);

const orderNumber = ref("");
const orderSecret = ref("");

const methodOptions = computed<PaymentOption[]>(() => {
  const hasDemo = methods.value.some((method) => method.provider_id === "demo");
  const sourceMethods = hasDemo
    ? methods.value.filter((method) => method.provider_id !== "demo")
    : methods.value;

  const baseOptions = sourceMethods.map((method) => ({
    option_id: method.provider_id,
    provider_id: method.provider_id,
    title: method.title,
    description: method.is_sandbox ? "Тестовый режим" : "Рабочий режим"
  }));

  if (hasDemo) {
    baseOptions.unshift({
      option_id: "demo_primary",
      provider_id: "demo",
      title: "Демо-оплата №1",
      description: "Тестовая оплата (демо-провайдер)"
    });
    baseOptions.splice(
      1,
      0,
      {
        option_id: "demo_secondary",
        provider_id: "demo",
        title: "Демо-оплата №2",
        description: "Тестовая оплата (демо-провайдер)"
      }
    );
  }

  return baseOptions;
});

const selectedMethod = computed(() =>
  methodOptions.value.find((option) => option.option_id === selectedOptionId.value) || null
);

const loadMethods = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await getCheckoutPaymentMethods();
    methods.value = response.data?.results || [];
    if (methodOptions.value.length > 0) {
      selectedOptionId.value = methodOptions.value[0].option_id;
    }
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Не удалось загрузить способы оплаты.";
  } finally {
    loading.value = false;
  }
};

const proceed = async () => {
  if (!selectedMethod.value || !orderNumber.value) {
    return;
  }
  submitting.value = true;
  error.value = null;
  try {
    const payload: { order_number: string; provider_id: string; order_secret?: string } = {
      order_number: orderNumber.value,
      provider_id: selectedMethod.value.provider_id
    };
    if (orderSecret.value) {
      payload.order_secret = orderSecret.value;
    }
    const response = await createPayment(payload);
    const paymentUrl = response.data?.payment_url;
    if (!paymentUrl) {
      throw new Error("Платёжная ссылка не получена.");
    }
    window.location.href = paymentUrl;
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Не удалось создать оплату.";
  } finally {
    submitting.value = false;
  }
};

onMounted(async () => {
  orderNumber.value = String(route.query.order_number || "");
  orderSecret.value = String(route.query.order_secret || "");
  if (!orderNumber.value) {
    error.value = "Не указан номер заказа.";
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

.actions {
  max-width: 520px;
  display: flex;
  justify-content: flex-end;
}

@media (max-width: 620px) {
  .actions {
    justify-content: stretch;
  }

  .actions .btn {
    width: 100%;
  }
}
</style>
