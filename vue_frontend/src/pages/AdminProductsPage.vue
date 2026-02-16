<template>
  <section class="page">
    <header class="heading">
      <div>
        <h1>Products</h1>
        <p>Manage catalog products with draft changes.</p>
      </div>
      <div class="toolbar">
        <button type="button" @click="openCreateModal" :disabled="isBusy">Add</button>
        <button type="button" @click="openBulkEdit" :disabled="isBusy">Edit (bulk)</button>
        <button type="button" @click="openBulkDelete" :disabled="isBusy">Delete (bulk)</button>
        <button type="button" @click="openBulkDiscount" :disabled="isBusy">
          Apply discounts (bulk)
        </button>
        <button type="button" @click="removeBulkDiscount" :disabled="isBusy">
          Remove discount
        </button>
      </div>
    </header>

    <p v-if="toast" class="toast">{{ toast }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="loading" class="loading">Loading products...</div>

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
            <th>Title</th>
            <th>Slug</th>
            <th>Description</th>
            <th>Price</th>
            <th>Category</th>
            <th>Visibility</th>
            <th>Images</th>
            <th>Discount %</th>
            <th>Status</th>
            <th>Actions</th>
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
                :disabled="row.status === 'deleted' || isBusy"
                @change="toggleSelect(row.id)"
              />
            </td>
            <td>
              <input
                v-model="row.title"
                type="text"
                :disabled="isRowLocked(row)"
                @input="markEdited(row)"
              />
            </td>
            <td>
              <div class="slug-cell">
                <input
                  :value="row.slug || ''"
                  type="text"
                  class="mono"
                  :disabled="isRowLocked(row)"
                  :class="{ invalid: Boolean(slugErrors[row.id]) }"
                  @input="onRowSlugInput(row, $event)"
                />
                <button
                  type="button"
                  class="icon"
                  :disabled="isRowLocked(row)"
                  title="Reset slug from title"
                  @click="resetRowSlug(row)"
                >
                  ↺
                </button>
              </div>
              <p v-if="slugErrors[row.id]" class="field-error">{{ slugErrors[row.id] }}</p>
            </td>
            <td>
              <textarea
                v-model="row.description"
                rows="2"
                :disabled="isRowLocked(row)"
                @input="markEdited(row)"
              />
            </td>
            <td>
              <div class="price-cell">
                <input
                  v-model.number="row.price"
                  type="number"
                  step="0.01"
                  min="0"
                  :disabled="isRowLocked(row)"
                  @input="markEdited(row)"
                />
                <div v-if="row.discount_percent && row.discount_percent > 0" class="discount">
                  <span class="old">{{ formatMoney(row.price) }}</span>
                  <span class="new">{{ formatMoney(applyDiscount(row.price, row.discount_percent)) }}</span>
                  <span class="badge">-{{ row.discount_percent }}%</span>
                </div>
              </div>
            </td>
            <td>
              <select
                v-model="row.category_id"
                :disabled="isRowLocked(row)"
                @change="markEdited(row)"
              >
                <option value="">No category</option>
                <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                  {{ cat.title || cat.slug || cat.id }}
                </option>
              </select>
            </td>
            <td>
              <select
                v-model="row.publish"
                :disabled="isRowLocked(row)"
                @change="markEdited(row)"
              >
                <option :value="true">Visible</option>
                <option :value="false">Hidden</option>
              </select>
            </td>
            <td>
              <button type="button" class="link" @click="openImages(row)" :disabled="isRowLocked(row)">
                Images
              </button>
            </td>
            <td>
              <div class="discount-input">
                <input
                  v-model.number="row.discount_percent"
                  type="number"
                  min="0"
                  max="100"
                  step="0.1"
                  :disabled="isRowLocked(row)"
                  @input="handleDiscountInput(row)"
                />
                <button
                  v-if="row.discount_percent > 0"
                  type="button"
                  class="link danger"
                  @click="clearRowDiscount(row)"
                  :disabled="isRowLocked(row)"
                >
                  ×
                </button>
              </div>
            </td>
            <td class="status-col">
              <span v-if="row.status !== 'clean'" class="badge status">{{ statusLabel(row) }}</span>
            </td>
            <td>
              <button
                type="button"
                class="icon danger"
                title="Mark product for deletion"
                @click="confirmDeleteRow(row)"
                :disabled="isBusy"
              >
                🗑
              </button>
            </td>
          </tr>
          <tr v-if="rows.length === 0">
            <td colspan="11" class="empty">No products found.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="pagination" v-if="pagination.total > 0">
      <button type="button" :disabled="isBusy || pagination.page <= 1" @click="changePage(-1)">
        Previous
      </button>
      <span>
        Page {{ pagination.page }} of {{ totalPages }} ({{ pagination.total }} items)
      </span>
      <button
        type="button"
        :disabled="isBusy || pagination.page >= totalPages"
        @click="changePage(1)"
      >
        Next
      </button>
    </footer>

    <div class="action-bar">
      <button type="button" class="secondary" @click="cancelChanges" :disabled="isBusy">
        Cancel changes
      </button>
      <button type="button" @click="applyChanges" :disabled="isBusy || !hasDraftChanges">
        Apply changes
      </button>
    </div>

    <div v-if="showCreateModal" class="modal">
      <div class="modal-card">
        <h2>Create product</h2>
        <div class="modal-body">
          <label>
            <span>Title *</span>
            <input v-model="createForm.title" type="text" @input="syncCreateSlug" />
          </label>
          <label>
            <span>Slug</span>
            <div class="slug-cell">
              <input
                v-model="createForm.slug"
                type="text"
                :class="{ invalid: Boolean(createSlugError) }"
                @input="onCreateSlugInput"
              />
              <button
                type="button"
                class="icon"
                title="Reset slug from title"
                @click="resetCreateSlug"
              >
                ↺
              </button>
            </div>
            <p v-if="createSlugError" class="field-error">{{ createSlugError }}</p>
          </label>
          <label>
            <span>Description</span>
            <textarea v-model="createForm.description" rows="3" />
          </label>
          <label>
            <span>Price *</span>
            <input v-model.number="createForm.price" type="number" min="0" step="0.01" />
          </label>
          <label>
            <span>Category</span>
            <select v-model="createForm.category_id">
              <option value="">No category</option>
              <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                {{ cat.title || cat.slug || cat.id }}
              </option>
            </select>
          </label>
          <label>
            <span>Visibility</span>
            <select v-model="createForm.publish">
              <option :value="true">Visible</option>
              <option :value="false">Hidden</option>
            </select>
          </label>
          <div class="images-inline">
            <span>Images</span>
            <button type="button" class="link" @click="openImagesForCreate">Attach</button>
            <span class="hint">{{ createImagesSummary }}</span>
          </div>
        </div>
        <div class="modal-actions">
          <button type="button" class="secondary" @click="closeCreateModal">Cancel</button>
          <button type="button" @click="confirmCreate">Add to draft</button>
        </div>
      </div>
    </div>

    <div v-if="showBulkEditModal" class="modal">
      <div class="modal-card">
        <h2>Bulk edit</h2>
        <div class="modal-body">
          <label>
            <span>Category</span>
            <select v-model="bulkEdit.category_id">
              <option value="__keep">Do not change</option>
              <option value="">No category</option>
              <option v-for="cat in categories" :key="cat.id" :value="cat.id">
                {{ cat.title || cat.slug || cat.id }}
              </option>
            </select>
          </label>
          <label>
            <span>Visibility</span>
            <select v-model="bulkEdit.visibility">
              <option value="__keep">Do not change</option>
              <option value="visible">Visible</option>
              <option value="hidden">Hidden</option>
            </select>
          </label>
          <div class="bulk-row">
            <label>
              <span>Change type</span>
              <select v-model="bulkEdit.priceType">
                <option value="percent">%</option>
                <option value="fixed">₽</option>
              </select>
            </label>
            <label>
              <span>Direction</span>
              <select v-model="bulkEdit.priceDirection">
                <option value="plus">+</option>
                <option value="minus">−</option>
              </select>
            </label>
            <label>
              <span>Value</span>
              <input v-model.number="bulkEdit.priceValue" type="number" step="0.01" min="0" />
            </label>
          </div>
          <p v-if="bulkEditError" class="error">{{ bulkEditError }}</p>
        </div>
        <div class="modal-actions">
          <button type="button" class="secondary" @click="closeBulkEdit">Cancel</button>
          <button type="button" @click="applyBulkEdit">Apply to draft</button>
        </div>
      </div>
    </div>

    <div v-if="showBulkDeleteModal" class="modal">
      <div class="modal-card">
        <h2>Delete products</h2>
        <p>
          Are you sure you want to delete {{ selectedIds.size }} products? This cannot be
          undone.
        </p>
        <div class="modal-actions">
          <button type="button" class="secondary" @click="closeBulkDelete">Cancel</button>
          <button type="button" class="danger" @click="confirmBulkDelete">Delete</button>
        </div>
      </div>
    </div>

    <div v-if="showBulkDiscountModal" class="modal">
      <div class="modal-card">
        <h2>Apply discount</h2>
        <div class="modal-body">
          <label>
            <span>Discount percent (0-100)</span>
            <input v-model.number="bulkDiscount" type="number" min="0" max="100" step="0.1" />
          </label>
        </div>
        <div class="modal-actions">
          <button type="button" class="secondary" @click="closeBulkDiscount">Cancel</button>
          <button type="button" @click="confirmBulkDiscount">Apply</button>
        </div>
      </div>
    </div>

    <div v-if="showDeleteModal" class="modal">
      <div class="modal-card">
        <h2>Delete product</h2>
        <p>
          Are you sure you want to delete "{{ deleteTarget?.title }}"? This cannot be undone.
        </p>
        <div class="modal-actions">
          <button type="button" class="secondary" @click="closeDeleteModal">Cancel</button>
          <button type="button" class="danger" @click="confirmDeleteSingle">Delete</button>
        </div>
      </div>
    </div>

    <div v-if="showImagesModal" class="modal">
      <div class="modal-card wide">
        <h2>Images</h2>
        <div class="modal-body">
          <div class="images-grid">
            <div v-for="(img, idx) in imageDraft" :key="img.id" class="image-tile">
              <img :src="img.preview" alt="Product image" />
              <div class="image-actions">
                <button type="button" class="link" @click="setThumbnail(idx)">
                  {{ idx === thumbnailIndex ? "Thumbnail" : "Make thumbnail" }}
                </button>
                <button type="button" class="link danger" @click="removeImage(idx)">Remove</button>
              </div>
            </div>
            <div v-if="imageDraft.length === 0" class="empty">No images attached.</div>
          </div>
          <input ref="fileInput" type="file" multiple accept="image/*" @change="handleImageFiles" />
        </div>
        <div class="modal-actions">
          <button type="button" class="secondary" @click="closeImagesModal">Close</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { adminApiClient } from "../api/adminClient";

type Category = {
  id: string;
  slug?: string | null;
  title?: string | null;
};

type ProductRow = {
  id: string;
  title: string;
  slug?: string | null;
  description?: string | null;
  price: number;
  category_id: string;
  publish: boolean;
  discount_percent: number;
  status: "clean" | "edited" | "new" | "deleted";
  original?: ProductSnapshot;
  images: ImageItem[];
  imageFiles: ImageItem[];
  thumbnailIndex: number | null;
};

type ProductSnapshot = Omit<ProductRow, "status" | "original" | "images" | "imageFiles"> & {
  images: ImageItem[];
  thumbnailIndex: number | null;
};

type ImageItem = {
  id: string;
  preview: string;
  file?: File;
  url?: string;
};

type PaginationState = {
  page: number;
  page_size: number;
  total: number;
};

const rows = ref<ProductRow[]>([]);
const categories = ref<Category[]>([]);
const selectedIds = ref<Set<string>>(new Set());
const loading = ref(false);
const committing = ref(false);
const error = ref<string | null>(null);
const toast = ref<string | null>(null);
const pagination = ref<PaginationState>({ page: 1, page_size: 20, total: 0 });

const showCreateModal = ref(false);
const showBulkEditModal = ref(false);
const showBulkDeleteModal = ref(false);
const showBulkDiscountModal = ref(false);
const showDeleteModal = ref(false);
const showImagesModal = ref(false);

const deleteTarget = ref<ProductRow | null>(null);
const imageTarget = ref<ProductRow | null>(null);
const imageDraft = ref<ImageItem[]>([]);
const thumbnailIndex = ref<number | null>(null);
const fileInput = ref<HTMLInputElement | null>(null);

const createForm = ref({
  title: "",
  slug: "",
  slugManuallyEdited: false,
  description: "",
  price: 0,
  category_id: "",
  publish: true,
  images: [] as ImageItem[]
});
const createSlugError = ref<string | null>(null);
const slugErrors = ref<Record<string, string>>({});

const bulkEdit = ref({
  category_id: "__keep",
  visibility: "__keep",
  priceType: "percent",
  priceDirection: "plus",
  priceValue: 0
});
const bulkEditError = ref<string | null>(null);

const bulkDiscount = ref(0);

const isBusy = computed(() => loading.value || committing.value);
const totalPages = computed(() =>
  Math.max(1, Math.ceil(pagination.value.total / pagination.value.page_size))
);
const allSelected = computed(() => {
  const selectable = rows.value.filter((row) => row.status !== "deleted");
  return selectable.length > 0 && selectable.every((row) => selectedIds.value.has(row.id));
});
const hasDraftChanges = computed(() =>
  rows.value.some((row) => row.status !== "clean")
);

const createImagesSummary = computed(() =>
  createForm.value.images.length > 0 ? `${createForm.value.images.length} attached` : "None"
);

const showToast = (message: string) => {
  toast.value = message;
  window.setTimeout(() => {
    toast.value = null;
  }, 2500);
};

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

const transliterateRu = (value: string) =>
  value
    .split("")
    .map((ch) => RU_TO_LATIN_MAP[ch] ?? ch)
    .join("");

const slugFromTitle = (value: string) => {
  const transliterated = transliterateRu(value.toLowerCase());
  return transliterated
    .trim()
    .replace(/[_\s]+/g, "-")
    .replace(/[^a-z0-9-]/g, "-")
    .replace(/-+/g, "-")
    .replace(/^-|-$/g, "");
};

const validateSlug = (slug: string) => {
  if (!slug) {
    return "Slug is required.";
  }
  if (!/^[a-z0-9-]+$/.test(slug)) {
    return "Slug can contain only latin letters, digits and '-'.";
  }
  return null;
};

const formatMoney = (value: number) => value.toFixed(2);

const applyDiscount = (price: number, discount: number) =>
  Number((price * (1 - discount / 100)).toFixed(2));

const isRowLocked = (row: ProductRow) => row.status === "deleted" || isBusy.value;

const statusLabel = (row: ProductRow) => {
  if (row.status === "new") return "new";
  if (row.status === "deleted") return "to delete";
  if (row.status === "edited") return "edited";
  return "";
};

const toggleSelect = (id: string) => {
  if (selectedIds.value.has(id)) {
    selectedIds.value.delete(id);
  } else {
    selectedIds.value.add(id);
  }
};

const toggleSelectAll = () => {
  if (allSelected.value) {
    selectedIds.value.clear();
  } else {
    rows.value.forEach((row) => {
      if (row.status !== "deleted") {
        selectedIds.value.add(row.id);
      }
    });
  }
};

const syncCreateSlug = () => {
  if (createForm.value.slugManuallyEdited) {
    return;
  }
  createForm.value.slug = slugFromTitle(createForm.value.title);
  createSlugError.value = validateSlug(createForm.value.slug);
};

const onCreateSlugInput = () => {
  createForm.value.slugManuallyEdited = true;
  createForm.value.slug = slugFromTitle(createForm.value.slug);
  createSlugError.value = validateSlug(createForm.value.slug);
};

const resetCreateSlug = () => {
  createForm.value.slugManuallyEdited = false;
  createForm.value.slug = slugFromTitle(createForm.value.title);
  createSlugError.value = validateSlug(createForm.value.slug);
};

const openCreateModal = () => {
  createForm.value = {
    title: "",
    slug: "",
    slugManuallyEdited: false,
    description: "",
    price: 0,
    category_id: "",
    publish: true,
    images: []
  };
  createSlugError.value = null;
  showCreateModal.value = true;
};

const closeCreateModal = () => {
  showCreateModal.value = false;
};

const confirmCreate = () => {
  if (!createForm.value.title.trim()) {
    showToast("Title is required.");
    return;
  }
  if (createForm.value.price <= 0) {
    showToast("Price must be greater than 0.");
    return;
  }
  createForm.value.slug = slugFromTitle(createForm.value.slug || createForm.value.title);
  createSlugError.value = validateSlug(createForm.value.slug);
  if (createSlugError.value) {
    return;
  }
  const id = `new-${Date.now()}-${Math.random().toString(16).slice(2)}`;
  const row: ProductRow = {
    id,
    title: createForm.value.title.trim(),
    slug: createForm.value.slug || slugFromTitle(createForm.value.title),
    description: createForm.value.description || "",
    price: Number(createForm.value.price),
    category_id: createForm.value.category_id,
    publish: createForm.value.publish,
    discount_percent: 0,
    status: "new",
    images: [...createForm.value.images],
    imageFiles: [...createForm.value.images],
    thumbnailIndex: createForm.value.images.length > 0 ? 0 : null
  };
  rows.value.unshift(row);
  closeCreateModal();
};

const onRowSlugInput = (row: ProductRow, event: Event) => {
  const target = event.target as HTMLInputElement;
  row.slug = slugFromTitle(target.value || "");
  const slugError = validateSlug(row.slug || "");
  if (slugError) {
    slugErrors.value[row.id] = slugError;
  } else {
    delete slugErrors.value[row.id];
  }
  markEdited(row);
};

const resetRowSlug = (row: ProductRow) => {
  row.slug = slugFromTitle(row.title || "");
  const slugError = validateSlug(row.slug || "");
  if (slugError) {
    slugErrors.value[row.id] = slugError;
  } else {
    delete slugErrors.value[row.id];
  }
  markEdited(row);
};

const markEdited = (row: ProductRow) => {
  if (row.status === "new" || row.status === "deleted") return;
  const original = row.original;
  if (!original) return;
  const isEdited =
    row.title !== original.title ||
    row.slug !== original.slug ||
    row.description !== original.description ||
    row.price !== original.price ||
    row.category_id !== original.category_id ||
    row.publish !== original.publish ||
    row.discount_percent !== original.discount_percent ||
    row.thumbnailIndex !== original.thumbnailIndex ||
    row.images.length !== original.images.length;
  row.status = isEdited ? "edited" : "clean";
};

const openBulkEdit = () => {
  if (selectedIds.value.size === 0) {
    showToast("No products selected.");
    return;
  }
  bulkEdit.value = {
    category_id: "__keep",
    visibility: "__keep",
    priceType: "percent",
    priceDirection: "plus",
    priceValue: 0
  };
  bulkEditError.value = null;
  showBulkEditModal.value = true;
};

const closeBulkEdit = () => {
  showBulkEditModal.value = false;
  bulkEditError.value = null;
};

const applyBulkEdit = () => {
  bulkEditError.value = null;
  const targets = rows.value.filter(
    (row) => selectedIds.value.has(row.id) && row.status !== "deleted"
  );
  if (targets.length === 0) {
    showToast("No products selected.");
    closeBulkEdit();
    return;
  }

  if (bulkEdit.value.priceValue && bulkEdit.value.priceValue > 0) {
    const updatedPrices = targets.map((row) => {
      const direction = bulkEdit.value.priceDirection === "plus" ? 1 : -1;
      if (bulkEdit.value.priceType === "percent") {
        const delta = row.price * (bulkEdit.value.priceValue / 100);
        return Number((row.price + direction * delta).toFixed(2));
      }
      return Number((row.price + direction * bulkEdit.value.priceValue).toFixed(2));
    });
    if (updatedPrices.some((price) => price < 0)) {
      bulkEditError.value = "Resulting price cannot be negative.";
      return;
    }
    targets.forEach((row, idx) => {
      row.price = updatedPrices[idx];
      markEdited(row);
    });
  }

  if (bulkEdit.value.category_id !== "__keep") {
    targets.forEach((row) => {
      row.category_id = bulkEdit.value.category_id;
      markEdited(row);
    });
  }

  if (bulkEdit.value.visibility !== "__keep") {
    const publishValue = bulkEdit.value.visibility === "visible";
    targets.forEach((row) => {
      row.publish = publishValue;
      markEdited(row);
    });
  }

  closeBulkEdit();
};

const openBulkDelete = () => {
  if (selectedIds.value.size === 0) {
    showToast("No products selected.");
    return;
  }
  showBulkDeleteModal.value = true;
};

const closeBulkDelete = () => {
  showBulkDeleteModal.value = false;
};

const confirmBulkDelete = () => {
  rows.value.forEach((row) => {
    if (selectedIds.value.has(row.id)) {
      row.status = "deleted";
    }
  });
  selectedIds.value.clear();
  closeBulkDelete();
};

const openBulkDiscount = () => {
  if (selectedIds.value.size === 0) {
    showToast("No products selected.");
    return;
  }
  bulkDiscount.value = 0;
  showBulkDiscountModal.value = true;
};

const closeBulkDiscount = () => {
  showBulkDiscountModal.value = false;
};

const confirmBulkDiscount = () => {
  if (bulkDiscount.value < 0 || bulkDiscount.value > 100) {
    showToast("Discount must be between 0 and 100.");
    return;
  }
  rows.value.forEach((row) => {
    if (selectedIds.value.has(row.id) && row.status !== "deleted") {
      row.discount_percent = bulkDiscount.value;
      markEdited(row);
    }
  });
  closeBulkDiscount();
};

const removeBulkDiscount = () => {
  if (selectedIds.value.size === 0) {
    showToast("No products selected.");
    return;
  }
  rows.value.forEach((row) => {
    if (selectedIds.value.has(row.id) && row.status !== "deleted") {
      row.discount_percent = 0;
      markEdited(row);
    }
  });
};

const confirmDeleteRow = (row: ProductRow) => {
  deleteTarget.value = row;
  showDeleteModal.value = true;
};

const closeDeleteModal = () => {
  showDeleteModal.value = false;
  deleteTarget.value = null;
};

const confirmDeleteSingle = () => {
  if (deleteTarget.value) {
    deleteTarget.value.status = "deleted";
    selectedIds.value.delete(deleteTarget.value.id);
  }
  closeDeleteModal();
};

const openImages = (row: ProductRow) => {
  imageTarget.value = row;
  imageDraft.value = [...row.images];
  thumbnailIndex.value = row.thumbnailIndex;
  showImagesModal.value = true;
};

const openImagesForCreate = () => {
  imageTarget.value = null;
  imageDraft.value = [...createForm.value.images];
  thumbnailIndex.value = 0;
  showImagesModal.value = true;
};

const closeImagesModal = () => {
  if (imageTarget.value) {
    imageTarget.value.images = [...imageDraft.value];
    imageTarget.value.imageFiles = [...imageDraft.value];
    imageTarget.value.thumbnailIndex = thumbnailIndex.value;
    markEdited(imageTarget.value);
  } else {
    createForm.value.images = [...imageDraft.value];
  }
  showImagesModal.value = false;
};

const setThumbnail = (index: number) => {
  thumbnailIndex.value = index;
};

const removeImage = (index: number) => {
  imageDraft.value.splice(index, 1);
  if (thumbnailIndex.value !== null && thumbnailIndex.value >= index) {
    thumbnailIndex.value = Math.max(0, thumbnailIndex.value - 1);
  }
};

const handleImageFiles = (event: Event) => {
  const input = event.target as HTMLInputElement;
  if (!input.files) return;
  Array.from(input.files).forEach((file) => {
    imageDraft.value.push({
      id: `${Date.now()}-${file.name}`,
      preview: URL.createObjectURL(file),
      file
    });
  });
  if (fileInput.value) {
    fileInput.value.value = "";
  }
};

const clampDiscount = (value: number) => Math.min(100, Math.max(0, value));

const handleDiscountInput = (row: ProductRow) => {
  const clamped = clampDiscount(Number(row.discount_percent || 0));
  if (row.discount_percent !== clamped) {
    row.discount_percent = clamped;
  }
  markEdited(row);
};

const clearRowDiscount = (row: ProductRow) => {
  row.discount_percent = 0;
  markEdited(row);
};

const changePage = async (direction: number) => {
  pagination.value.page = pagination.value.page + direction;
  await loadProducts();
};

const buildRowFromApi = (item: any): ProductRow => {
  const price = Number(item.price ?? 0);
  const discount = Number(item.discount_percent ?? 0);
  const categoryId = item.category?.id || "";
  const row: ProductRow = {
    id: String(item.id),
    title: item.title || "",
    slug: item.slug || "",
    description: item.description || "",
    price: Number.isNaN(price) ? 0 : price,
    category_id: categoryId,
    publish: true,
    discount_percent: Number.isNaN(discount) ? 0 : discount,
    status: "clean",
    images: [],
    imageFiles: [],
    thumbnailIndex: null
  };
  row.original = {
    ...row,
    images: [],
    thumbnailIndex: null
  };
  return row;
};

const loadProducts = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await adminApiClient.get("/admin/catalog/products/", {
      params: {
        page: pagination.value.page,
        page_size: pagination.value.page_size
      }
    });
    rows.value = (response.data.results || []).map(buildRowFromApi);
    slugErrors.value = {};
    pagination.value = response.data.pagination || pagination.value;
    selectedIds.value.clear();
  } catch (err) {
    console.error(err);
    error.value = "Failed to load products.";
  } finally {
    loading.value = false;
  }
};

const loadCategories = async () => {
  try {
    const response = await adminApiClient.get("/admin/catalog/categories/", {
      params: {
        page: 1,
        page_size: 100
      }
    });
    categories.value = response.data.results || [];
  } catch (err) {
    console.error(err);
    showToast("Failed to load categories.");
  }
};

const cancelChanges = async () => {
  await loadProducts();
};

const ensureValidSlugs = (list: ProductRow[]) => {
  let hasErrors = false;
  for (const row of list) {
    row.slug = slugFromTitle(row.slug || "");
    const slugError = validateSlug(row.slug || "");
    if (slugError) {
      slugErrors.value[row.id] = slugError;
      hasErrors = true;
    } else {
      delete slugErrors.value[row.id];
    }
  }
  return !hasErrors;
};

const isSlugConflictResponse = (err: any) =>
  err?.response?.status === 400 &&
  err?.response?.data &&
  Object.prototype.hasOwnProperty.call(err.response.data, "slug");

const getSlugConflictMessage = (err: any) => {
  const raw = err?.response?.data?.slug;
  if (Array.isArray(raw) && raw.length > 0) {
    return String(raw[0]);
  }
  if (typeof raw === "string" && raw.trim()) {
    return raw.trim();
  }
  return "This slug is already in use.";
};

const applyChanges = async () => {
  committing.value = true;
  error.value = null;
  let imageUploadSkipped = false;
  try {
    const created = rows.value.filter((row) => row.status === "new");
    const updated = rows.value.filter((row) => row.status === "edited");
    const deleted = rows.value.filter((row) => row.status === "deleted");

    if (!ensureValidSlugs([...created, ...updated])) {
      showToast("Please fix slug errors before applying changes.");
      error.value = "Validation failed.";
      return;
    }

    for (const row of created) {
      if (row.imageFiles.length > 0) {
        imageUploadSkipped = true;
      }
      try {
        await adminApiClient.post("/admin/catalog/products/", {
          title: row.title,
          slug: row.slug,
          description: row.description,
          price: row.price,
          currency: "RUB",
          category: row.category_id || "",
          publish: row.publish,
          discount_percent: row.discount_percent
        });
      } catch (err: any) {
        if (isSlugConflictResponse(err)) {
          slugErrors.value[row.id] = getSlugConflictMessage(err);
          showToast("Slug already in use");
          error.value = "Slug already in use.";
          return;
        }
        throw err;
      }
    }

    for (const row of updated) {
      if (row.imageFiles.length > 0) {
        imageUploadSkipped = true;
      }
      try {
        await adminApiClient.put(`/admin/catalog/products/${row.id}/`, {
          title: row.title,
          slug: row.slug,
          description: row.description,
          price: row.price,
          currency: "RUB",
          category: row.category_id || "",
          publish: row.publish,
          discount_percent: row.discount_percent
        });
      } catch (err: any) {
        if (isSlugConflictResponse(err)) {
          slugErrors.value[row.id] = getSlugConflictMessage(err);
          showToast("Slug already in use");
          error.value = "Slug already in use.";
          return;
        }
        throw err;
      }
    }

    for (const row of deleted) {
      if (row.id.startsWith("new-")) continue;
      await adminApiClient.delete(`/admin/catalog/products/${row.id}/`);
    }

    if (imageUploadSkipped) {
      showToast("Image upload not implemented yet. Image changes were skipped.");
    } else {
      showToast("Changes applied.");
    }
    await loadProducts();
  } catch (err) {
    console.error(err);
    error.value = "Failed to apply changes. Draft kept for retry.";
  } finally {
    committing.value = false;
  }
};

onMounted(async () => {
  await Promise.all([loadCategories(), loadProducts()]);
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
  min-width: 1000px;
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

.table input,
.table select,
.table textarea {
  width: 100%;
  padding: 6px;
  border: 1px solid #d6cbb8;
  background: #fff;
}

.table input.invalid {
  border-color: #b11e1e;
}

.table textarea {
  resize: vertical;
}

.mono {
  font-family: "Courier New", Courier, monospace;
}

.slug-cell {
  display: flex;
  align-items: center;
  gap: 8px;
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
  flex-shrink: 0;
}

.icon:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}

.field-error {
  margin: 4px 0 0;
  color: #b11e1e;
  font-size: 12px;
}

.price-cell {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.discount {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-size: 12px;
}

.discount .old {
  text-decoration: line-through;
  color: #8a7b68;
}

.discount .new {
  font-weight: 600;
  color: #2f4b2f;
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

.discount-input {
  display: flex;
  align-items: center;
  gap: 6px;
}

.badge.status {
  margin-left: 8px;
}

.status-col {
  min-width: 110px;
}

.link {
  background: none;
  border: none;
  color: #4b3c2f;
  cursor: pointer;
  text-decoration: underline;
  padding: 0;
}

.danger {
  color: #b11e1e;
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

.pagination {
  display: flex;
  align-items: center;
  gap: 12px;
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

.modal-card.wide {
  width: min(900px, 100%);
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

.bulk-row {
  display: grid;
  grid-template-columns: repeat(3, minmax(0, 1fr));
  gap: 12px;
}

.images-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(140px, 1fr));
  gap: 12px;
}

.image-tile {
  border: 1px solid #d6cbb8;
  padding: 8px;
  background: #fffdf8;
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.image-tile img {
  width: 100%;
  height: 100px;
  object-fit: cover;
  border-radius: 4px;
}

.image-actions {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.images-inline {
  display: flex;
  align-items: center;
  gap: 12px;
}

.hint {
  color: #6f5f4c;
  font-size: 12px;
}
</style>
