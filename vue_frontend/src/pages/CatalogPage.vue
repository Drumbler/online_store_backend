<template>
  <section class="page">
    <h1>Catalog</h1>

    <form class="filters" @submit.prevent="applyFilters">
      <div class="filter-group">
        <label for="search">Search</label>
        <input id="search" v-model="search" placeholder="Search by title" />
      </div>

      <div class="filter-group">
        <label for="ordering">Sort</label>
        <select id="ordering" v-model="ordering">
          <option value="">Default</option>
          <option value="price">Price (low to high)</option>
          <option value="-price">Price (high to low)</option>
          <option value="title">Title (A-Z)</option>
          <option value="-title">Title (Z-A)</option>
        </select>
      </div>

      <button type="submit">Apply</button>
    </form>

    <div class="layout">
      <aside class="categories">
        <h2>Categories</h2>
        <button class="category-btn" :class="{ active: !selectedCategory }" @click="setCategory('')">
          All
        </button>
        <button
          v-for="category in catalogStore.categories"
          :key="category.id"
          class="category-btn"
          :class="{ active: category.slug === selectedCategory }"
          @click="setCategory(category.slug || '')"
        >
          {{ category.title || category.slug || category.id }}
        </button>
      </aside>

      <section class="products">
        <div v-if="catalogStore.loading" class="status">Loading...</div>
        <div v-else-if="catalogStore.error" class="status error">{{ catalogStore.error }}</div>

        <div v-else class="grid">
          <article v-for="product in catalogStore.products" :key="product.id" class="card">
            <RouterLink :to="`/p/${product.slug}`" class="card-link">
              <img
                v-if="product.image_url"
                :src="product.image_url"
                :alt="product.title"
                class="card-image"
              />
              <div v-else class="card-placeholder">No image</div>
              <h3>{{ product.title }}</h3>
            </RouterLink>
            <div class="price">
              <template v-if="hasDiscount(product)">
                <span class="old">{{ product.price }} {{ product.currency }}</span>
                <span class="new">{{ discountedPrice(product) }} {{ product.currency }}</span>
                <span class="badge">-{{ product.discount_percent }}%</span>
              </template>
              <template v-else>
                <span>{{ product.price }} {{ product.currency }}</span>
              </template>
            </div>
            <button @click="addToCart(product.id)">Add to cart</button>
          </article>
        </div>

        <div class="pagination">
          <button :disabled="page <= 1" @click="changePage(page - 1)">Prev</button>
          <span>Page {{ page }} of {{ totalPages }}</span>
          <button :disabled="page >= totalPages" @click="changePage(page + 1)">Next</button>
        </div>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useCartStore } from "../stores/cart";
import { useCatalogStore } from "../stores/catalog";

const router = useRouter();
const route = useRoute();
const catalogStore = useCatalogStore();
const cartStore = useCartStore();

const search = ref("");
const ordering = ref("");
const selectedCategory = ref("");

const page = computed(() => catalogStore.pagination.page || 1);
const totalPages = computed(() => {
  const total = catalogStore.pagination.total || 0;
  const pageSize = catalogStore.pagination.page_size || 1;
  return Math.max(1, Math.ceil(total / pageSize));
});

const normalizeQuery = () => {
  search.value = typeof route.query.search === "string" ? route.query.search : "";
  ordering.value = typeof route.query.ordering === "string" ? route.query.ordering : "";
  selectedCategory.value = typeof route.query.category === "string" ? route.query.category : "";
};

const applyFilters = () => {
  const query: Record<string, string> = {};
  if (search.value.trim()) {
    query.search = search.value.trim();
  }
  if (ordering.value) {
    query.ordering = ordering.value;
  }
  if (selectedCategory.value) {
    query.category = selectedCategory.value;
  }
  query.page = "1";
  router.push({ path: "/", query });
};

const setCategory = (slug: string) => {
  selectedCategory.value = slug;
  applyFilters();
};

const changePage = (nextPage: number) => {
  const query = { ...route.query, page: String(nextPage) };
  router.push({ path: "/", query });
};

const addToCart = (productId?: string) => {
  if (!productId) {
    return;
  }
  cartStore.addToCart(productId, 1);
};

const hasDiscount = (product: any) => {
  const discount = Number(product.discount_percent || 0);
  return discount > 0;
};

const discountedPrice = (product: any) => {
  if (product.discounted_price) {
    return product.discounted_price;
  }
  const price = Number(product.price || 0);
  const discount = Number(product.discount_percent || 0);
  const discounted = price * (1 - discount / 100);
  return discounted.toFixed(2);
};

onMounted(() => {
  catalogStore.fetchCategories();
});

watch(
  () => route.query,
  (query) => {
    normalizeQuery();
    catalogStore.fetchProductsFromRouteQuery(query);
  },
  { immediate: true }
);
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.filters {
  display: flex;
  gap: 12px;
  flex-wrap: wrap;
  align-items: flex-end;
}

.filter-group {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.layout {
  display: grid;
  grid-template-columns: 220px 1fr;
  gap: 24px;
}

.categories {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.category-btn {
  text-align: left;
  padding: 6px 10px;
  background: #fff;
  border: 1px solid #ddd;
}

.category-btn.active {
  border-color: #333;
  font-weight: 600;
}

.products {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(220px, 1fr));
  gap: 16px;
}

.card {
  background: #fff;
  padding: 12px;
  border: 1px solid #e0e0e0;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.card-link {
  text-decoration: none;
  color: inherit;
}

.card-image {
  width: 100%;
  height: 140px;
  object-fit: cover;
  border: 1px solid #eee;
}

.card-placeholder {
  width: 100%;
  height: 140px;
  display: flex;
  align-items: center;
  justify-content: center;
  background: #f0f0f0;
  color: #666;
  border: 1px solid #eee;
}

.price {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-weight: 600;
}

.price .old {
  text-decoration: line-through;
  color: #8a7b68;
  font-weight: 400;
}

.price .new {
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
  width: fit-content;
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

.pagination {
  display: flex;
  gap: 12px;
  align-items: center;
}

@media (max-width: 900px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
