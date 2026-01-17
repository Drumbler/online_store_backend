<template>
  <div class="app">
    <header v-if="showPublicNav" class="navbar">
      <nav class="nav-links">
        <RouterLink to="/">Catalog</RouterLink>
        <RouterLink to="/categories">Categories</RouterLink>
        <RouterLink to="/cart">Cart ({{ cartCount }})</RouterLink>
        <RouterLink to="/orders">{{ isLoggedIn ? "My orders" : "Track order" }}</RouterLink>
        <RouterLink to="/admin">Admin</RouterLink>
        <RouterLink v-if="!isLoggedIn" to="/login">Login</RouterLink>
        <RouterLink v-if="!isLoggedIn" to="/register">Register</RouterLink>
        <button v-if="isLoggedIn" class="link-button" type="button" @click="handleLogout">
          Logout
        </button>
      </nav>
    </header>
    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute, useRouter } from "vue-router";

import { useCartStore } from "./stores/cart";
import { useAuthStore } from "./stores/auth";

const cartStore = useCartStore();
const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();

const cartCount = computed(() => cartStore.cartCount);
const isLoggedIn = computed(() => Boolean(authStore.token));
const showPublicNav = computed(() => !route.path.startsWith("/admin"));

const handleLogout = async () => {
  await authStore.logout();
  await router.push("/");
};
</script>

<style scoped>
.navbar {
  padding: 16px;
  border-bottom: 1px solid #ddd;
}

.nav-links {
  display: flex;
  gap: 16px;
  align-items: center;
}

.nav-links a {
  color: #333;
  text-decoration: none;
}

.nav-links a.router-link-active {
  font-weight: 600;
}

.link-button {
  background: none;
  border: none;
  padding: 0;
  color: #333;
  cursor: pointer;
  font: inherit;
}

.main {
  padding: 16px;
}
</style>
