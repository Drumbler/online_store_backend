<template>
  <section class="page">
    <h1>Categories</h1>

    <div v-if="catalogStore.loading" class="status">Loading...</div>
    <div v-else-if="catalogStore.error" class="status error">{{ catalogStore.error }}</div>

    <ul v-else class="list">
      <li v-for="category in catalogStore.categories" :key="category.id">
        <button class="link" @click="goToCategory(category.slug || '')">
          {{ category.title || category.slug || category.id }}
        </button>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useRouter } from "vue-router";
import { useCatalogStore } from "../stores/catalog";

const catalogStore = useCatalogStore();
const router = useRouter();

const goToCategory = (slug: string) => {
  if (!slug) {
    router.push({ path: "/" });
    return;
  }
  router.push({ path: "/", query: { category: slug } });
};

onMounted(() => {
  catalogStore.fetchCategories();
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
  gap: 8px;
}

.link {
  background: none;
  border: none;
  color: #1a1a1a;
  text-align: left;
  padding: 0;
}

.link:hover {
  text-decoration: underline;
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
