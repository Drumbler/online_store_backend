<template>
  <section class="page">
    <header class="heading">
      <div>
        <h1>Заказы</h1>
        <p>Управление статусами заказов и мониторинг доставки.</p>
      </div>
      <div class="controls">
        <label class="field">
          <span>Размер страницы</span>
          <select v-model.number="pageSize" :disabled="isBusy" @change="applyFilters">
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
          </select>
        </label>
      </div>
    </header>

    <p v-if="toast" class="toast">{{ toast }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="filters">
      <label>
        <span>Поиск</span>
        <input
          v-model="query"
          type="text"
          placeholder="Номер заказа или пользователь"
          :disabled="isBusy"
          @keyup.enter="applyFilters"
        />
      </label>
      <label>
        <span>Тип доставки</span>
        <select v-model="deliveryTypeFilter" :disabled="isBusy">
          <option value="">Все</option>
          <option value="courier">Курьер</option>
          <option value="pickup">Самовывоз</option>
        </select>
      </label>
      <label>
        <span>Статус</span>
        <select v-model="statusFilter" :disabled="isBusy">
          <option value="">Все</option>
          <option v-for="item in statusOptions" :key="item.value" :value="item.value">
            {{ item.label }}
          </option>
        </select>
      </label>
      <button type="button" :disabled="isBusy" @click="applyFilters">Применить</button>
    </div>

    <div v-if="loading" class="loading">Загрузка заказов...</div>

    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>Номер заказа</th>
            <th>Пользователь</th>
            <th>Сумма</th>
            <th>Тип доставки</th>
            <th>Статус заказа</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row.id"
            :class="{ edited: row.statusDraft !== row.originalStatus }"
          >
            <td class="mono">#{{ row.order_number }}</td>
            <td>{{ row.user_display }}</td>
            <td>{{ row.total }}</td>
            <td>{{ deliveryTypeLabel(row.delivery_type) }}</td>
            <td>
              <div class="status-cell">
                <select v-model="row.statusDraft" :disabled="isBusy">
                  <option
                    v-for="item in statusOptionsForRow(row)"
                    :key="`${row.id}-${item.value}`"
                    :value="item.value"
                  >
                    {{ item.label }}
                  </option>
                </select>
                <span class="hint">Оплата: {{ paymentStatusLabel(row.payment_status) }}</span>
              </div>
            </td>
          </tr>
          <tr v-if="rows.length === 0">
            <td colspan="5" class="empty">Заказы не найдены.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="pagination" v-if="pagination.total > 0">
      <button type="button" :disabled="isBusy || pagination.page <= 1" @click="changePage(-1)">
        Назад
      </button>
      <span>Страница {{ pagination.page }} из {{ totalPages }} ({{ pagination.total }} шт.)</span>
      <button
        type="button"
        :disabled="isBusy || pagination.page >= totalPages"
        @click="changePage(1)"
      >
        Вперед
      </button>
    </footer>

    <div class="action-bar">
      <button type="button" class="secondary" :disabled="isBusy || !hasDraftChanges" @click="cancelChanges">
        Отменить изменения
      </button>
      <button type="button" :disabled="isBusy || !hasDraftChanges" @click="applyChanges">
        Применить изменения
      </button>
    </div>
  </section>
</template>

<script setup lang="ts">
/** Логика страницы и обработчики UI состояния заказов. */
import { computed, onMounted, ref } from "vue";

import { adminApiClient } from "../api/adminClient";

type StatusOption = {
  value: string;
  label: string;
};

type OrderRow = {
  id: number;
  order_number: number;
  user_display: string;
  total: string;
  delivery_type: string;
  payment_status: string;
  status: string;
  originalStatus: string;
  statusDraft: string;
};

type PaginationState = {
  page: number;
  page_size: number;
  total: number;
};

const STATUS_OPTIONS: StatusOption[] = [
  { value: "awaiting_payment", label: "Ожидает оплаты" },
  { value: "ready_for_dispatch", label: "Готов к отгрузке" },
  { value: "handover_to_delivery", label: "Передан в доставку" },
  { value: "in_transit", label: "В пути" },
  { value: "ready_for_pickup", label: "Готов к выдаче" },
  { value: "delivered", label: "Доставлен" },
  { value: "delivery_failed", label: "Ошибка доставки" },
  { value: "cancelled", label: "Отменен" }
];

const rows = ref<OrderRow[]>([]);
const loading = ref(false);
const committing = ref(false);
const error = ref<string | null>(null);
const toast = ref<string | null>(null);

const query = ref("");
const deliveryTypeFilter = ref("");
const statusFilter = ref("");
const pageSize = ref(20);
const pagination = ref<PaginationState>({ page: 1, page_size: 20, total: 0 });

const isBusy = computed(() => loading.value || committing.value);
const totalPages = computed(() =>
  Math.max(1, Math.ceil((pagination.value.total || 0) / (pagination.value.page_size || 1)))
);
const hasDraftChanges = computed(() =>
  rows.value.some((row) => row.statusDraft !== row.originalStatus)
);
const statusOptions = computed(() => STATUS_OPTIONS);

const showToast = (message: string) => {
  toast.value = message;
  window.setTimeout(() => {
    if (toast.value === message) {
      toast.value = null;
    }
  }, 2500);
};

const deliveryTypeLabel = (value: string) => {
  if (value === "courier") return "Курьер";
  if (value === "pickup") return "Самовывоз";
  return "—";
};

const paymentStatusLabel = (value: string) => {
  if (value === "pending_payment") return "Ожидает оплату";
  if (value === "payment_failed") return "Оплата не прошла";
  if (value === "paid") return "Оплачен";
  if (value === "cancelled") return "Отменен";
  return value || "—";
};

const normalizeRows = (list: any[]): OrderRow[] =>
  list.map((item) => {
    const status = String(item?.status || "awaiting_payment");
    return {
      id: Number(item?.id),
      order_number: Number(item?.order_number),
      user_display: String(item?.user_display || "Гость"),
      total: String(item?.total || "0.00"),
      delivery_type: String(item?.delivery_type || ""),
      payment_status: String(item?.payment_status || ""),
      status,
      originalStatus: status,
      statusDraft: status
    };
  });

const loadOrders = async (page = pagination.value.page) => {
  loading.value = true;
  error.value = null;
  try {
    const response = await adminApiClient.get("/admin/orders/", {
      params: {
        page,
        page_size: pageSize.value,
        q: query.value.trim() || undefined,
        delivery_type: deliveryTypeFilter.value || undefined,
        status: statusFilter.value || undefined
      }
    });
    rows.value = normalizeRows(response.data?.results || []);
    pagination.value = response.data?.pagination || pagination.value;
  } catch (err: any) {
    console.error(err);
    error.value = err?.response?.data?.detail || "Не удалось загрузить заказы.";
  } finally {
    loading.value = false;
  }
};

const applyFilters = async () => {
  pagination.value.page = 1;
  pagination.value.page_size = pageSize.value;
  await loadOrders(1);
};

const changePage = async (step: number) => {
  const nextPage = pagination.value.page + step;
  if (nextPage < 1 || nextPage > totalPages.value) {
    return;
  }
  pagination.value.page = nextPage;
  await loadOrders(nextPage);
};

const cancelChanges = () => {
  rows.value = rows.value.map((row) => ({
    ...row,
    statusDraft: row.originalStatus
  }));
};

const statusOptionsForRow = (row: OrderRow) => {
  if (row.payment_status === "cancelled") {
    return STATUS_OPTIONS.filter((item) => item.value === "cancelled");
  }
  if (row.payment_status !== "paid") {
    return STATUS_OPTIONS.filter(
      (item) => item.value === "awaiting_payment" || item.value === "cancelled"
    );
  }
  return STATUS_OPTIONS.filter((item) => item.value !== "awaiting_payment");
};

const applyChanges = async () => {
  const changedRows = rows.value.filter((row) => row.statusDraft !== row.originalStatus);
  if (changedRows.length === 0) {
    return;
  }

  committing.value = true;
  error.value = null;
  let updated = 0;
  try {
    for (const row of changedRows) {
      await adminApiClient.patch(`/admin/orders/${row.id}/status/`, { status: row.statusDraft });
      updated += 1;
    }
    await loadOrders(pagination.value.page);
    showToast(`Статусы обновлены: ${updated}`);
  } catch (err: any) {
    console.error(err);
    const detail = err?.response?.data?.detail;
    const statusErrors = err?.response?.data?.status;
    if (Array.isArray(statusErrors) && statusErrors.length > 0) {
      error.value = String(statusErrors[0]);
    } else {
      error.value = detail || "Не удалось обновить статусы заказов.";
    }
  } finally {
    committing.value = false;
  }
};

onMounted(async () => {
  await loadOrders(1);
});
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.heading h1 {
  margin: 0;
}

.heading p {
  margin: 4px 0 0;
  color: #6f5f4c;
}

.controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 14px;
}

.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(220px, 1fr));
  gap: 12px;
  align-items: end;
}

.filters label {
  display: flex;
  flex-direction: column;
  gap: 6px;
  color: #4b3c2f;
}

.loading {
  padding: 16px;
  border: 1px dashed #c6b59a;
  background: #fffdf8;
}

.table-wrap {
  overflow-x: auto;
  background: #fffdf8;
  border: 1px solid #e2d5be;
}

.table {
  width: 100%;
  border-collapse: collapse;
  min-width: 950px;
}

.table th,
.table td {
  padding: 12px;
  border-bottom: 1px solid #eadfc9;
  text-align: left;
  vertical-align: middle;
}

.table th {
  background: #f3ead8;
  font-weight: 600;
}

.table tr:last-child td {
  border-bottom: none;
}

.table tr.edited {
  background: #fff7eb;
}

.mono {
  font-family: "Courier New", Courier, monospace;
}

.status-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hint {
  color: #7b6c58;
  font-size: 12px;
}

.empty {
  text-align: center;
  color: #6f5f4c;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
}

.pagination button,
.action-bar button,
.filters button {
  padding: 8px 12px;
  border: 1px solid #c6b59a;
  background: #f6efe1;
  cursor: pointer;
}

.pagination button:disabled,
.action-bar button:disabled,
.filters button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.action-bar {
  position: sticky;
  bottom: 0;
  z-index: 30;
  display: flex;
  justify-content: flex-end;
  gap: 10px;
  padding: 12px;
  border: 1px solid #d8ccb8;
  background: #f4ecdf;
}

.secondary {
  background: #efe7d9;
}

.toast {
  margin: 0;
  padding: 8px 12px;
  border: 1px solid #bfe3bf;
  background: #e7f7e7;
}

.error {
  margin: 0;
  color: #b11e1e;
  padding: 8px 12px;
  border: 1px solid #f2b3b3;
  background: #ffe1e1;
}
</style>
