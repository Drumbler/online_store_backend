<template>
  <section class="page">
    <header class="heading">
      <div>
        <h1>Отзывы</h1>
        <p>Модерация видимости отзывов с черновыми изменениями.</p>
      </div>
      <div class="toolbar">
        <button type="button" class="icon" title="Скрыть выбранные" :disabled="isBusy" @click="hideSelected">
          🙈
        </button>
        <button type="button" class="icon" title="Показать выбранные" :disabled="isBusy" @click="unhideSelected">
          👁
        </button>
      </div>
    </header>

    <p v-if="toast" class="toast">{{ toast }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="filters">
      <label>
        <span>Поиск</span>
        <input v-model="searchQuery" type="text" placeholder="Комментарий, автор, заказ, товар..." :disabled="isBusy" />
      </label>
      <label>
        <span>Рейтинг</span>
        <select v-model="ratingFilter" :disabled="isBusy">
          <option value="">Все</option>
          <option value="4">4★+</option>
          <option value="3">3★+</option>
          <option value="2">2★+</option>
          <option value="1">1★+</option>
        </select>
      </label>
      <label>
        <span>Статус</span>
        <select v-model="statusFilter" :disabled="isBusy">
          <option value="all">Все</option>
          <option value="true">Опубликован</option>
          <option value="false">Скрыт</option>
        </select>
      </label>
      <label>
        <span>Сортировка</span>
        <select v-model="sortFilter" :disabled="isBusy">
          <option value="created_desc">Сначала новые</option>
          <option value="created_asc">Сначала старые</option>
          <option value="rating_desc">Рейтинг: высокий к низкому</option>
          <option value="rating_asc">Рейтинг: низкий к высокому</option>
        </select>
      </label>
      <button type="button" @click="applyFilters" :disabled="isBusy">Применить</button>
    </div>

    <div v-if="loading" class="loading">Загрузка отзывов...</div>

    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>
              <input
                type="checkbox"
                :checked="allSelected"
                :disabled="draftReviews.length === 0 || isBusy"
                @change="toggleSelectAll"
              />
            </th>
            <th>Товар</th>
            <th>Рейтинг</th>
            <th>Автор</th>
            <th>Дата</th>
            <th>Опубликован</th>
            <th>Содержимое</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="row in draftReviews" :key="row.id">
            <td>
              <input
                type="checkbox"
                :checked="selectedIds.has(row.id)"
                :disabled="isBusy"
                @change="toggleSelect(row.id)"
              />
            </td>
            <td>
              <div class="product-cell">
                <img v-if="row.product_image_url" :src="row.product_image_url" :alt="row.product_title || row.product_id" />
                <div v-else class="thumb-fallback">Нет изображения</div>
                <div class="product-meta">
                  <strong>{{ row.product_title || row.product_id }}</strong>
                  <span class="muted">{{ row.product_id }}</span>
                </div>
              </div>
            </td>
            <td>
              <div class="rating-cell">
                <StarRatingDisplay :rating="row.rating" />
                <span>{{ row.rating.toFixed(1) }}</span>
              </div>
            </td>
            <td>
              {{ row.is_anonymous ? "Аноним" : row.author_display_name }}
            </td>
            <td>{{ formatDate(row.created_at) }}</td>
            <td>
              <input
                type="checkbox"
                :checked="row.is_published"
                :disabled="isBusy"
                @change="togglePublished(row.id)"
              />
            </td>
            <td>
              <div class="content-cell">
                <span class="preview">{{ previewText(row) }}</span>
                <button type="button" class="icon" title="Развернуть" :disabled="isBusy" @click="openContentModal(row)">
                  ⤢
                </button>
              </div>
            </td>
          </tr>
          <tr v-if="draftReviews.length === 0">
            <td colspan="7" class="empty">Отзывы не найдены.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="pagination" v-if="pagination.total > 0">
      <button type="button" :disabled="isBusy || pagination.page <= 1" @click="changePage(-1)">
        Назад
      </button>
      <span>
        Страница {{ pagination.page }} из {{ totalPages }} ({{ pagination.total }} шт.)
      </span>
      <button type="button" :disabled="isBusy || pagination.page >= totalPages" @click="changePage(1)">
        Вперед
      </button>
    </footer>

    <div class="action-bar">
      <button type="button" class="secondary" :disabled="isBusy" @click="cancelChanges">
        Отменить изменения
      </button>
      <button type="button" :disabled="isBusy || !hasDraftChanges" @click="applyChanges">
        Применить изменения
      </button>
    </div>

    <div v-if="expandedReview" class="modal" @click.self="expandedReview = null">
      <div class="modal-card">
        <h2>Содержимое отзыва</h2>
        <p><strong>Товар:</strong> {{ expandedReview.product_title || expandedReview.product_id }}</p>
        <p><strong>Автор:</strong> {{ expandedReview.author_display_name }}</p>
        <p><strong>Плюсы:</strong> {{ expandedReview.pros || "—" }}</p>
        <p><strong>Минусы:</strong> {{ expandedReview.cons || "—" }}</p>
        <p><strong>Комментарий:</strong> {{ expandedReview.comment || "—" }}</p>
        <div class="modal-actions">
          <button type="button" @click="expandedReview = null">Закрыть</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
/** Логика страницы и обработчики UI состояния. */
import { computed, onMounted, ref } from "vue";

import { adminApiClient } from "../api/adminClient";
import StarRatingDisplay from "../components/StarRatingDisplay.vue";

type ReviewRow = {
  id: number;
  product_id: string;
  product_title: string | null;
  product_image_url: string | null;
  rating: number;
  pros: string | null;
  cons: string | null;
  comment: string | null;
  author_display_name: string;
  is_anonymous: boolean;
  order_number: string | null;
  created_at: string;
  is_published: boolean;
};

type Pagination = {
  page: number;
  page_size: number;
  total: number;
};

const originalReviews = ref<ReviewRow[]>([]);
const draftReviews = ref<ReviewRow[]>([]);
const selectedIds = ref<Set<number>>(new Set());
const expandedReview = ref<ReviewRow | null>(null);

const loading = ref(false);
const committing = ref(false);
const error = ref<string | null>(null);
const toast = ref<string | null>(null);

const searchQuery = ref("");
const ratingFilter = ref("");
const statusFilter = ref("all");
const sortFilter = ref<"created_desc" | "created_asc" | "rating_desc" | "rating_asc">("created_desc");

const pagination = ref<Pagination>({ page: 1, page_size: 20, total: 0 });

const isBusy = computed(() => loading.value || committing.value);
const totalPages = computed(() =>
  Math.max(1, Math.ceil((pagination.value.total || 0) / (pagination.value.page_size || 1)))
);
const allSelected = computed(
  () => draftReviews.value.length > 0 && draftReviews.value.every((row) => selectedIds.value.has(row.id))
);
const hasDraftChanges = computed(() => {
  const originalById = new Map(originalReviews.value.map((row) => [row.id, row]));
  return draftReviews.value.some((row) => {
    const original = originalById.get(row.id);
    return original ? original.is_published !== row.is_published : false;
  });
});

const showToast = (message: string) => {
  toast.value = message;
  window.setTimeout(() => {
    if (toast.value === message) {
      toast.value = null;
    }
  }, 2500);
};

const cloneRows = (rows: ReviewRow[]) => rows.map((row) => ({ ...row }));

const fetchReviews = async (page = pagination.value.page) => {
  loading.value = true;
  error.value = null;
  try {
    const response = await adminApiClient.get("/admin/reviews/", {
      params: {
        page,
        page_size: pagination.value.page_size,
        q: searchQuery.value.trim() || undefined,
        rating_gte: ratingFilter.value || undefined,
        is_published: statusFilter.value,
        sort: sortFilter.value
      }
    });
    const payload = response.data;
    const rows = (payload?.results || []) as ReviewRow[];
    originalReviews.value = cloneRows(rows);
    draftReviews.value = cloneRows(rows);
    pagination.value = payload?.pagination || pagination.value;
    selectedIds.value.clear();
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Не удалось загрузить отзывы.";
  } finally {
    loading.value = false;
  }
};

const applyFilters = async () => {
  await fetchReviews(1);
};

const changePage = async (step: number) => {
  const nextPage = pagination.value.page + step;
  if (nextPage < 1 || nextPage > totalPages.value) {
    return;
  }
  await fetchReviews(nextPage);
};

const toggleSelect = (id: number) => {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id);
  } else {
    selectedIds.value.add(id);
  }
  selectedIds.value = new Set(selectedIds.value);
};

const toggleSelectAll = () => {
  if (allSelected.value) {
    selectedIds.value.clear();
  } else {
    selectedIds.value = new Set(draftReviews.value.map((row) => row.id));
  }
};

const togglePublished = (id: number) => {
  const row = draftReviews.value.find((item) => item.id === id);
  if (!row) {
    return;
  }
  row.is_published = !row.is_published;
};

const setSelectedPublished = (value: boolean) => {
  if (selectedIds.value.size === 0) {
    showToast("Отзывы не выбраны");
    return;
  }
  draftReviews.value.forEach((row) => {
    if (selectedIds.value.has(row.id)) {
      row.is_published = value;
    }
  });
};

const hideSelected = () => setSelectedPublished(false);
const unhideSelected = () => setSelectedPublished(true);

const cancelChanges = () => {
  draftReviews.value = cloneRows(originalReviews.value);
  selectedIds.value.clear();
};

const applyChanges = async () => {
  const originalById = new Map(originalReviews.value.map((row) => [row.id, row]));
  const toPublish: number[] = [];
  const toHide: number[] = [];
  draftReviews.value.forEach((row) => {
    const original = originalById.get(row.id);
    if (!original || original.is_published === row.is_published) {
      return;
    }
    if (row.is_published) {
      toPublish.push(row.id);
    } else {
      toHide.push(row.id);
    }
  });

  if (toPublish.length === 0 && toHide.length === 0) {
    return;
  }

  committing.value = true;
  error.value = null;
  try {
    if (toPublish.length > 0) {
      await adminApiClient.post("/admin/reviews/bulk/", { ids: toPublish, is_published: true });
    }
    if (toHide.length > 0) {
      await adminApiClient.post("/admin/reviews/bulk/", { ids: toHide, is_published: false });
    }
    await fetchReviews(pagination.value.page);
    showToast("Изменения применены.");
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Не удалось применить изменения.";
  } finally {
    committing.value = false;
  }
};

const openContentModal = (row: ReviewRow) => {
  expandedReview.value = row;
};

const previewText = (row: ReviewRow) => {
  const value = row.comment || row.pros || row.cons || "";
  if (!value) {
    return "—";
  }
  return value.length > 100 ? `${value.slice(0, 100)}...` : value;
};

const formatDate = (value: string) => {
  const date = new Date(value);
  return Number.isNaN(date.getTime()) ? value : date.toLocaleString();
};

onMounted(async () => {
  await fetchReviews(1);
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
  justify-content: space-between;
  align-items: center;
  gap: 16px;
}

.heading h1 {
  margin: 0;
}

.heading p {
  margin: 4px 0 0;
  color: #6b5a45;
}

.toolbar {
  display: flex;
  gap: 8px;
}

.filters {
  display: grid;
  grid-template-columns: repeat(auto-fit, minmax(180px, 1fr));
  gap: 10px;
  align-items: end;
}

.filters label {
  display: flex;
  flex-direction: column;
  gap: 4px;
  color: #4b3c2f;
}

.filters input,
.filters select,
.filters button {
  min-height: 34px;
}

.table-wrap {
  overflow: auto;
  border: 1px solid #d6cbb8;
  background: #fff;
}

.table {
  width: 100%;
  border-collapse: collapse;
  min-width: 1100px;
}

.table th,
.table td {
  border-bottom: 1px solid #eee2ce;
  padding: 10px;
  text-align: left;
  vertical-align: top;
}

.table thead th {
  background: #faf5eb;
  color: #4b3c2f;
  font-weight: 600;
}

.product-cell {
  display: flex;
  gap: 10px;
  align-items: center;
}

.product-cell img,
.thumb-fallback {
  width: 46px;
  height: 46px;
  object-fit: cover;
  border: 1px solid #e6dac4;
  background: #f3ede2;
}

.thumb-fallback {
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 11px;
  color: #7a6a55;
}

.product-meta {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.product-meta .muted {
  color: #7d6f5d;
  font-size: 12px;
}

.rating-cell {
  display: inline-flex;
  align-items: center;
  gap: 8px;
}

.content-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.preview {
  max-width: 300px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  color: #5b4c3b;
}

.pagination {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 12px;
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

.toast {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid #bfe3bf;
  background: #e7f7e7;
}

.error {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid #f2b3b3;
  background: #ffe1e1;
  color: #8d2f2f;
}

.loading {
  color: #5f4f3f;
}

.empty {
  text-align: center;
  color: #85745f;
  padding: 18px;
}

.icon {
  min-width: 34px;
  min-height: 34px;
  border: 1px solid #d0c1aa;
  border-radius: 8px;
  background: #fff;
  cursor: pointer;
}

.icon:disabled {
  opacity: 0.5;
  cursor: not-allowed;
}

.secondary {
  background: #efe7d9;
}

.modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.35);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 16px;
  z-index: 40;
}

.modal-card {
  width: min(700px, 100%);
  max-height: 90vh;
  overflow: auto;
  border: 1px solid #d9ccb8;
  background: #fff;
  padding: 16px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
}
</style>
