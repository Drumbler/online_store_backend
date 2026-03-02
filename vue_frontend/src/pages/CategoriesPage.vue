<template>
  <section class="page bg-app text-app">
    <h1>Категории</h1>

    <div v-if="catalogStore.loading" class="state-box">Загрузка...</div>
    <div v-else-if="catalogStore.error" class="state-box error">{{ catalogStore.error }}</div>

    <ul v-else class="list">
      <li v-for="category in catalogStore.categories" :key="category.id">
        <button type="button" class="category-link btn btn-neutral" @click="goToCategory(category.slug || '')">
          {{ category.title || category.slug || category.id }}
        </button>
      </li>
    </ul>
  </section>
</template>

<script setup lang="ts">
/** Логика страницы и обработчики UI состояния. */
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
  gap: 10px;
}

.category-link {
  width: 100%;
  justify-content: flex-start;
  color: var(--text);
  border-color: var(--border);
}

.category-link:hover {
  color: var(--primary);
  border-color: var(--primary);
}

</style>
