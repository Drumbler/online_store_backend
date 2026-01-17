<template>
  <div class="admin">
    <header class="admin-nav">
      <nav class="admin-links">
        <RouterLink to="/admin/products">Products</RouterLink>
        <RouterLink to="/admin/categories">Categories</RouterLink>
        <RouterLink to="/admin/orders">Orders</RouterLink>
        <RouterLink to="/admin/reports">Reports</RouterLink>
        <RouterLink to="/">Back to shop</RouterLink>
        <button class="link-button" type="button" @click="handleLogout">Logout</button>
      </nav>
    </header>
    <section class="admin-content">
      <RouterView />
    </section>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import { useAdminAuthStore } from "../stores/adminAuth";

const router = useRouter();
const adminAuthStore = useAdminAuthStore();

const handleLogout = async () => {
  adminAuthStore.clearToken();
  await router.push("/");
};
</script>

<style scoped>
.admin {
  min-height: 100vh;
  background: #f8f4ec;
}

.admin-nav {
  padding: 16px;
  border-bottom: 1px solid #d6cbb8;
  background: #f0e7d7;
}

.admin-links {
  display: flex;
  flex-wrap: wrap;
  gap: 16px;
  align-items: center;
}

.admin-links a {
  color: #4b3c2f;
  text-decoration: none;
  font-weight: 600;
}

.admin-links a.router-link-active {
  text-decoration: underline;
}

.link-button {
  background: none;
  border: none;
  padding: 0;
  color: #4b3c2f;
  cursor: pointer;
  font: inherit;
  font-weight: 600;
}

.admin-content {
  padding: 24px;
}
</style>
