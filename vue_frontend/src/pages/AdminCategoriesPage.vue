<template>
  <section class="page">
    <header class="heading">
      <div>
        <h1>Категории</h1>
        <p>Управление категориями с черновыми изменениями.</p>
      </div>
      <div class="toolbar">
        <button type="button" @click="openCreateModal" :disabled="isBusy">Добавить</button>
        <button type="button" @click="openBulkDelete" :disabled="isBusy">Удалить</button>
      </div>
    </header>

    <p v-if="toast" class="toast">{{ toast }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="loading" class="loading">Загрузка категорий...</div>

    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>
              <input
                type="checkbox"
                :checked="allSelected"
                :disabled="rows.length === 0"
                @change="toggleSelectAll"
              />
            </th>
            <th>Название</th>
            <th>Слаг</th>
            <th>Количество товаров</th>
            <th>Расчетная скидка</th>
            <th>Скидка категории (черновик)</th>
            <th>Статус</th>
            <th>Действия</th>
          </tr>
        </thead>
        <tbody>
          <tr
            v-for="row in rows"
            :key="row.id"
            :class="{
              muted: row.status === 'deleted',
              edited: row.status === 'edited',
              new: row.status === 'new'
            }"
          >
            <td>
              <input
                type="checkbox"
                :checked="selectedIds.has(row.id)"
                :disabled="isRowLocked(row)"
                @change="toggleSelect(row.id)"
              />
            </td>
            <td>
              <input
                v-model="row.title"
                type="text"
                :disabled="isRowLocked(row)"
                @input="onTitleInput(row)"
              />
            </td>
            <td>
              <div class="slug-cell">
                <input
                  :value="row.slug"
                  type="text"
                  class="mono"
                  :disabled="isRowLocked(row)"
                  :class="{ invalid: Boolean(row.slugError) }"
                  @input="onSlugInput(row, $event)"
                />
                <button
                  type="button"
                  class="icon"
                  :disabled="isRowLocked(row)"
                  title="Обновить slug из названия"
                  @click="resetSlug(row)"
                >
                  ↻
                </button>
              </div>
              <p v-if="row.slugError" class="field-error">{{ row.slugError }}</p>
            </td>
            <td>{{ row.product_count }}</td>
            <td>{{ derivedDiscountLabel(row) }}</td>
            <td>
              <div class="discount-cell">
                <input
                  v-model.number="row.discountInput"
                  type="number"
                  min="0"
                  max="100"
                  step="1"
                  :disabled="isRowLocked(row)"
                  @input="onDiscountInput(row)"
                />
                <span class="hint" title="Применяется после кнопки «Применить изменения»">Применяется после кнопки «Применить изменения»</span>
              </div>
            </td>
            <td class="status-col">
              <span v-if="row.status !== 'clean'" class="badge status">{{ statusLabel(row) }}</span>
            </td>
            <td class="actions">
              <button
                type="button"
                class="icon danger"
                :disabled="isBusy"
                title="Пометить категорию на удаление"
                @click="openDeleteRowConfirm(row)"
              >
                🗑
              </button>
            </td>
          </tr>
          <tr v-if="rows.length === 0">
            <td colspan="8" class="empty">Категории не найдены.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <div class="action-bar">
      <button type="button" class="secondary" :disabled="isBusy" @click="cancelChanges">
        Отменить изменения
      </button>
      <button type="button" :disabled="isBusy || !hasDraftChanges" @click="applyChanges">
        Применить изменения
      </button>
    </div>

    <div v-if="showCreateModal" class="modal">
      <div class="modal-card">
        <h2>Создать категорию</h2>
        <div class="modal-body">
          <label>
            <span>Название *</span>
            <input v-model="createForm.title" type="text" @input="syncCreateSlug" />
          </label>
          <label>
            <span>Слаг</span>
            <div class="slug-cell">
              <input
                v-model="createForm.slug"
                type="text"
                :class="{ invalid: Boolean(createForm.slugError) }"
                @input="onCreateSlugInput"
              />
              <button type="button" class="icon" title="Обновить slug из названия" @click="resetCreateSlug">
                ↻
              </button>
            </div>
            <p v-if="createForm.slugError" class="field-error">{{ createForm.slugError }}</p>
          </label>
        </div>
        <div class="modal-actions">
          <button type="button" class="secondary" @click="closeCreateModal">Отмена</button>
          <button type="button" @click="confirmCreate">Добавить в черновик</button>
        </div>
      </div>
    </div>

    <div v-if="confirmDialog" class="modal">
      <div class="modal-card">
        <h2>{{ confirmDialog.title }}</h2>
        <p>{{ confirmDialog.message }}</p>
        <div class="modal-actions">
          <button type="button" class="secondary" @click="closeConfirm">Отмена</button>
          <button
            type="button"
            :class="confirmDialog.danger ? 'danger' : ''"
            @click="runConfirmAction"
          >
            Подтвердить
          </button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
/** Логика страницы и обработчики UI состояния. */
import { computed, onMounted, ref } from "vue";
import { adminApiClient } from "../api/adminClient";

type CategoryRow = {
  id: string;
  title: string;
  slug: string;
  product_count: number;
  derived_discount_percent: number | null;
  derived_discount_is_mixed: boolean;
  discountInput: number | null;
  originalDiscountInput: number | null;
  slugManuallyEdited: boolean;
  slugError: string | null;
  status: "clean" | "new" | "edited" | "deleted";
  original?: {
    title: string;
    slug: string;
  };
};

type ConfirmDialog = {
  title: string;
  message: string;
  danger?: boolean;
  action: () => void;
};

const rows = ref<CategoryRow[]>([]);
const selectedIds = ref<Set<string>>(new Set());
const loading = ref(false);
const committing = ref(false);
const error = ref<string | null>(null);
const toast = ref<string | null>(null);

const showCreateModal = ref(false);
const createForm = ref({
  title: "",
  slug: "",
  slugError: null as string | null,
  slugManuallyEdited: false
});

const confirmDialog = ref<ConfirmDialog | null>(null);

const RU_TO_LATIN_MAP: Record<string, string> = {
  а: "a",
  б: "b",
  в: "v",
  г: "g",
  д: "d",
  е: "e",
  ё: "e",
  ж: "zh",
  з: "z",
  и: "i",
  й: "y",
  к: "k",
  л: "l",
  м: "m",
  н: "n",
  о: "o",
  п: "p",
  р: "r",
  с: "s",
  т: "t",
  у: "u",
  ф: "f",
  х: "kh",
  ц: "ts",
  ч: "ch",
  ш: "sh",
  щ: "sch",
  ъ: "",
  ы: "y",
  ь: "",
  э: "e",
  ю: "yu",
  я: "ya"
};

const isBusy = computed(() => loading.value || committing.value);
const allSelected = computed(() => {
  const selectable = rows.value.filter((row) => row.status !== "deleted");
  return selectable.length > 0 && selectable.every((row) => selectedIds.value.has(row.id));
});
const hasDraftChanges = computed(() =>
  rows.value.some(
    (row) => row.status !== "clean" || !isSameDiscount(row.discountInput, row.originalDiscountInput)
  )
);

const showToast = (message: string) => {
  toast.value = message;
  window.setTimeout(() => {
    toast.value = null;
  }, 2500);
};

const transliterateRu = (value: string) =>
  value
    .split("")
    .map((ch) => RU_TO_LATIN_MAP[ch] ?? ch)
    .join("");

const slugFromTitle = (value: string) =>
  transliterateRu(value.toLowerCase())
    .trim()
    .replace(/[_\s]+/g, "-")
    .replace(/[^a-z0-9-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");

const validateSlug = (slug: string) => {
  if (!slug) return "Слаг обязателен.";
  if (!/^[a-z0-9-]+$/.test(slug)) return "Слаг может содержать только латинские буквы, цифры и '-'.";
  return null;
};

const derivedDiscountLabel = (row: CategoryRow) => {
  if (row.derived_discount_is_mixed) return "смешанная";
  if (row.derived_discount_percent === null || row.derived_discount_percent === undefined) return "—";
  return `${row.derived_discount_percent}%`;
};

const statusLabel = (row: CategoryRow) => {
  if (row.status === "new") return "новая";
  if (row.status === "edited") return "изменена";
  if (row.status === "deleted") return "к удалению";
  return "";
};

const isRowLocked = (row: CategoryRow) => row.status === "deleted" || isBusy.value;

const normalizeDiscount = (value: number | null | undefined) => {
  if (value === null || value === undefined) return null;
  if (Number.isNaN(Number(value))) return null;
  return Math.min(100, Math.max(0, Math.round(Number(value))));
};

const isSameDiscount = (a: number | null | undefined, b: number | null | undefined) =>
  normalizeDiscount(a) === normalizeDiscount(b);

const markEdited = (row: CategoryRow) => {
  if (row.status === "new" || row.status === "deleted") return;
  if (!row.original) return;
  const changed =
    row.title !== row.original.title ||
    row.slug !== row.original.slug ||
    !isSameDiscount(row.discountInput, row.originalDiscountInput);
  row.status = changed ? "edited" : "clean";
};

const onDiscountInput = (row: CategoryRow) => {
  if (row.discountInput === null || row.discountInput === undefined || row.discountInput === "") {
    row.discountInput = null;
  } else {
    row.discountInput = normalizeDiscount(row.discountInput);
  }
  markEdited(row);
};

const mapRowFromApi = (item: any): CategoryRow => ({
  id: String(item.id),
  title: item.title || "",
  slug: item.slug || "",
  product_count: Number(item.product_count || 0),
  derived_discount_percent:
    item.derived_discount_percent === null || item.derived_discount_percent === undefined
      ? null
      : Number(item.derived_discount_percent),
  derived_discount_is_mixed: Boolean(item.derived_discount_is_mixed),
  discountInput: null,
  originalDiscountInput: null,
  slugManuallyEdited: false,
  slugError: null,
  status: "clean",
  original: {
    title: item.title || "",
    slug: item.slug || ""
  }
});

const loadCategories = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await adminApiClient.get("/admin/catalog/categories/", {
      params: { page: 1, page_size: 100 }
    });
    rows.value = (response.data.results || []).map(mapRowFromApi);
    selectedIds.value.clear();
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Не удалось загрузить категории.";
  } finally {
    loading.value = false;
  }
};

const toggleSelect = (id: string) => {
  if (selectedIds.value.has(id)) selectedIds.value.delete(id);
  else selectedIds.value.add(id);
};

const toggleSelectAll = () => {
  if (allSelected.value) {
    selectedIds.value.clear();
    return;
  }
  rows.value.forEach((row) => {
    if (row.status !== "deleted") selectedIds.value.add(row.id);
  });
};

const onTitleInput = (row: CategoryRow) => {
  if (row.status === "new" && !row.slugManuallyEdited) {
    row.slug = slugFromTitle(row.title);
    row.slugError = validateSlug(row.slug);
  }
  markEdited(row);
};

const onSlugInput = (row: CategoryRow, event: Event) => {
  const target = event.target as HTMLInputElement;
  row.slugManuallyEdited = true;
  row.slug = slugFromTitle(target.value || "");
  row.slugError = validateSlug(row.slug);
  markEdited(row);
};

const resetSlug = (row: CategoryRow) => {
  row.slugManuallyEdited = false;
  row.slug = slugFromTitle(row.title || "");
  row.slugError = validateSlug(row.slug);
  markEdited(row);
};

const openCreateModal = () => {
  createForm.value = {
    title: "",
    slug: "",
    slugError: null,
    slugManuallyEdited: false
  };
  showCreateModal.value = true;
};

const closeCreateModal = () => {
  showCreateModal.value = false;
};

const syncCreateSlug = () => {
  if (createForm.value.slugManuallyEdited) return;
  createForm.value.slug = slugFromTitle(createForm.value.title);
  createForm.value.slugError = validateSlug(createForm.value.slug);
};

const onCreateSlugInput = () => {
  createForm.value.slugManuallyEdited = true;
  createForm.value.slug = slugFromTitle(createForm.value.slug);
  createForm.value.slugError = validateSlug(createForm.value.slug);
};

const resetCreateSlug = () => {
  createForm.value.slugManuallyEdited = false;
  createForm.value.slug = slugFromTitle(createForm.value.title);
  createForm.value.slugError = validateSlug(createForm.value.slug);
};

const confirmCreate = () => {
  const title = createForm.value.title.trim();
  if (!title) {
    showToast("Название обязательно.");
    return;
  }
  const slug = slugFromTitle(createForm.value.slug || title);
  const slugError = validateSlug(slug);
  createForm.value.slugError = slugError;
  if (slugError) return;

  rows.value.unshift({
    id: `new-${Date.now()}-${Math.random().toString(16).slice(2)}`,
    title,
    slug,
    product_count: 0,
    derived_discount_percent: null,
    derived_discount_is_mixed: false,
    discountInput: null,
    originalDiscountInput: null,
    slugManuallyEdited: createForm.value.slugManuallyEdited,
    slugError: null,
    status: "new",
  });
  closeCreateModal();
};

const openBulkDelete = () => {
  const targets = rows.value.filter(
    (row) => selectedIds.value.has(row.id) && row.status !== "deleted"
  );
  if (targets.length === 0) {
    showToast("Категории не выбраны.");
    return;
  }
  confirmDialog.value = {
    title: "Удаление категорий",
    message: `Удалить ${targets.length} категорий? Это действие необратимо.`,
    danger: true,
    action: () => {
      targets.forEach((row) => {
        row.status = "deleted";
      });
      selectedIds.value.clear();
    }
  };
};

const openDeleteRowConfirm = (row: CategoryRow) => {
  confirmDialog.value = {
    title: "Удаление категории",
    message: `Удалить категорию «${row.title}»? Это действие необратимо.`,
    danger: true,
    action: () => {
      row.status = "deleted";
      selectedIds.value.delete(row.id);
    }
  };
};

const closeConfirm = () => {
  confirmDialog.value = null;
};

const runConfirmAction = () => {
  if (!confirmDialog.value) return;
  const action = confirmDialog.value.action;
  closeConfirm();
  action();
};

const isSlugConflictResponse = (err: any) =>
  err?.response?.status === 400 &&
  err?.response?.data &&
  Object.prototype.hasOwnProperty.call(err.response.data, "slug");

const getSlugErrorMessage = (err: any) => {
  const raw = err?.response?.data?.slug;
  if (Array.isArray(raw) && raw.length > 0) return String(raw[0]);
  if (typeof raw === "string" && raw.trim()) return raw.trim();
  return "Этот slug уже используется.";
};

const validateRowSlugs = (targets: CategoryRow[]) => {
  let ok = true;
  targets.forEach((row) => {
    row.slug = slugFromTitle(row.slug || "");
    row.slugError = validateSlug(row.slug);
    if (row.slugError) ok = false;
  });
  return ok;
};

const cancelChanges = async () => {
  await loadCategories();
};

const applyChanges = async () => {
  committing.value = true;
  error.value = null;

  try {
    const created = rows.value.filter((row) => row.status === "new");
    const updated = rows.value.filter((row) => row.status === "edited" && !row.id.startsWith("new-"));
    const deleted = rows.value.filter(
      (row) => row.status === "deleted" && !row.id.startsWith("new-")
    );
    const discountChanged = rows.value.filter(
      (row) => row.status !== "deleted" && !isSameDiscount(row.discountInput, row.originalDiscountInput)
    );

    if (!validateRowSlugs([...created, ...updated])) {
      showToast("Исправьте ошибки slug перед применением изменений.");
      error.value = "Ошибка валидации.";
      return;
    }

    for (const row of created) {
      try {
        const response = await adminApiClient.post("/admin/catalog/categories/", {
          title: row.title.trim(),
          slug: row.slug
        });
        const createdId = String(response.data?.id || "");
        if (createdId) {
          row.id = createdId;
        }
      } catch (err: any) {
        if (isSlugConflictResponse(err)) {
          row.slugError = getSlugErrorMessage(err);
          showToast("Слаг уже используется");
          error.value = "Слаг уже используется.";
          return;
        }
        throw err;
      }
    }

    for (const row of updated) {
      try {
        await adminApiClient.put(`/admin/catalog/categories/${row.id}/`, {
          title: row.title.trim(),
          slug: row.slug
        });
      } catch (err: any) {
        if (isSlugConflictResponse(err)) {
          row.slugError = getSlugErrorMessage(err);
          showToast("Слаг уже используется");
          error.value = "Слаг уже используется.";
          return;
        }
        throw err;
      }
    }

    for (const row of deleted) {
      await adminApiClient.delete(`/admin/catalog/categories/${row.id}/`);
    }

    for (const row of discountChanged) {
      const value = normalizeDiscount(row.discountInput);
      if (value === null) {
        continue;
      }
      if (value === 0) {
        await adminApiClient.post(`/admin/catalog/categories/${row.id}/remove-discount/`);
      } else {
        await adminApiClient.post(`/admin/catalog/categories/${row.id}/apply-discount/`, {
          discount_percent: value
        });
      }
    }

    showToast("Изменения применены.");
    await loadCategories();
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Не удалось применить изменения. Черновик сохранен для повторной попытки.";
  } finally {
    committing.value = false;
  }
};

onMounted(() => {
  loadCategories();
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
  flex-wrap: wrap;
  justify-content: space-between;
  gap: 16px;
}

.heading p {
  color: #6f5f4c;
}

.toolbar {
  display: flex;
  flex-wrap: wrap;
  gap: 12px;
}

.toolbar button,
.action-bar button {
  padding: 8px 12px;
  border: 1px solid #c6b59a;
  background: #f6efe1;
  cursor: pointer;
}

.toolbar button:disabled,
.action-bar button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.toast {
  margin: 0;
  padding: 8px 12px;
  background: #f0e7d7;
  border: 1px solid #d6cbb8;
}

.error {
  margin: 0;
  color: #b11e1e;
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
  min-width: 1050px;
}

.table th,
.table td {
  padding: 10px;
  border-bottom: 1px solid #eadfc9;
  text-align: left;
  vertical-align: top;
}

.table th {
  background: #f3ead8;
  font-weight: 600;
}

.table input:not([type="checkbox"]):not([type="radio"]),
.table select {
  width: 100%;
  padding: 6px;
  border: 1px solid #d6cbb8;
  background: #fff;
}

.table input.invalid {
  border-color: #b11e1e;
}

.mono {
  font-family: "Courier New", Courier, monospace;
}

.slug-cell {
  display: flex;
  align-items: center;
  gap: 8px;
}

.field-error {
  margin: 4px 0 0;
  color: #b11e1e;
  font-size: 12px;
}

.actions {
  display: flex;
  align-items: center;
  flex-wrap: wrap;
  gap: 6px;
}

.status-col {
  min-width: 110px;
}

.discount-cell {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.hint {
  color: #6f5f4c;
  font-size: 12px;
}

.icon {
  width: 30px;
  height: 30px;
  padding: 0;
  border: 1px solid #c6b59a;
  background: #f6efe1;
  cursor: pointer;
  display: inline-flex;
  align-items: center;
  justify-content: center;
}

.icon:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.danger {
  color: #b11e1e;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: #efe4cf;
  color: #4b3c2f;
  font-size: 12px;
}

.badge.status.action {
  background: #f2ead8;
}

.muted {
  opacity: 0.6;
  background: #f6efe1;
}

.edited {
  background: #fff7e6;
}

.new {
  background: #eef8f0;
}

.empty {
  text-align: center;
  color: #6f5f4c;
}

.action-bar {
  position: sticky;
  bottom: 0;
  display: flex;
  justify-content: flex-end;
  gap: 12px;
  padding: 12px;
  background: #f6efe1;
  border-top: 1px solid #d6cbb8;
}

.secondary {
  background: #fff;
}

.link {
  background: none;
  border: none;
  color: #4b3c2f;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
}

.modal {
  position: fixed;
  inset: 0;
  background: rgba(0, 0, 0, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
  padding: 24px;
  z-index: 40;
}

.modal-card {
  width: min(600px, 100%);
  background: #fff;
  border: 1px solid #e2d5be;
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.modal-body {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.modal-body label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.modal-actions {
  display: flex;
  justify-content: flex-end;
  gap: 12px;
}
</style>
