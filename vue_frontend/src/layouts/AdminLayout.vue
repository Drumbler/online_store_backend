<template>
  <div class="admin bg-app text-app">
    <header class="admin-nav">
      <nav class="admin-links">
        <RouterLink to="/admin/products">Товары</RouterLink>
        <RouterLink to="/admin/categories">Категории</RouterLink>
        <RouterLink to="/admin/orders">Заказы</RouterLink>
        <RouterLink to="/admin/reviews">Отзывы</RouterLink>
        <RouterLink to="/admin/integrations">Интеграции</RouterLink>
        <RouterLink to="/admin/appearance">Оформление</RouterLink>
        <RouterLink to="/admin/reports">Отчеты</RouterLink>
        <RouterLink to="/admin/users">Пользователи</RouterLink>
        <RouterLink to="/">В магазин</RouterLink>
        <button class="link-button" type="button" @click="handleLogout">Выйти</button>
      </nav>
    </header>
    <section class="admin-content">
      <RouterView />
    </section>
  </div>
</template>

<script setup lang="ts">
/** Логика страницы и обработчики UI состояния. */
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const router = useRouter();
const authStore = useAuthStore();

const handleLogout = async () => {
  await authStore.logout();
  await router.push("/");
};
</script>

<style scoped>
.admin {
  min-height: 100vh;
  background: var(--bg);
}

.admin-nav {
  padding: 16px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  box-shadow: var(--shadow);
}

.admin-links {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
}

.admin-links a {
  color: var(--text);
  text-decoration: none;
  font-weight: 600;
}

.admin-links a.router-link-active {
  color: var(--primary);
  text-decoration: underline;
}

.link-button {
  background: none;
  border: none;
  padding: 0;
  color: var(--text);
  cursor: pointer;
  font: inherit;
  font-weight: 600;
}

.admin-content {
  padding: 24px;
}
</style>
