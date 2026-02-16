<template>
  <div class="app">
    <header v-if="showPublicNav" class="navbar">
      <nav class="nav-links">
        <div class="nav-left">
          <RouterLink to="/">Catalog</RouterLink>
          <RouterLink to="/categories">Categories</RouterLink>
          <RouterLink to="/orders">{{ isLoggedIn ? "My orders" : "Track order" }}</RouterLink>
          <RouterLink v-if="isAdmin" to="/admin">Admin</RouterLink>
          <RouterLink v-if="!isLoggedIn" to="/login">Login</RouterLink>
          <RouterLink v-if="!isLoggedIn" to="/register">Register</RouterLink>
        </div>
        <div class="nav-right">
          <RouterLink v-if="isLoggedIn" to="/account" class="account-button">
            Личный кабинет
          </RouterLink>
          <RouterLink to="/cart" class="cart-button" aria-label="Cart">
            <svg
              class="cart-icon"
              viewBox="0 0 24 24"
              role="img"
              aria-hidden="true"
              focusable="false"
            >
              <path
                d="M7 18c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zm10 0c-1.1 0-2 .9-2 2s.9 2 2 2 2-.9 2-2-.9-2-2-2zM6.2 6l.5 2h10.9l-1.1 5H7.4L6 4H3V2h4.1l.8 4h12.2c.7 0 1.2.6 1.1 1.3l-1.4 6.4c-.1.7-.7 1.3-1.5 1.3H7.1c-.7 0-1.3-.5-1.5-1.2L4.1 2.8"
                fill="currentColor"
              />
            </svg>
            <span v-if="cartCount" class="cart-badge">{{ cartCount }}</span>
          </RouterLink>
        </div>
      </nav>
    </header>
    <main class="main">
      <RouterView />
    </main>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useRoute } from "vue-router";

import { useCartStore } from "./stores/cart";
import { useAuthStore } from "./stores/auth";

const cartStore = useCartStore();
const authStore = useAuthStore();
const route = useRoute();

const cartCount = computed(() => cartStore.cartCount);
const isLoggedIn = computed(() => Boolean(authStore.token));
const isAdmin = computed(
  () =>
    Boolean(
      authStore.user?.is_admin || authStore.user?.is_staff || authStore.user?.is_superuser
    )
);
const showPublicNav = computed(() => !route.path.startsWith("/admin"));

</script>

<style scoped>
.navbar {
  padding: 16px;
  border-bottom: 1px solid #ddd;
}

.nav-links {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.nav-left {
  display: flex;
  gap: 16px;
  align-items: center;
  flex-wrap: wrap;
}

.nav-right {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-left: auto;
}

.nav-links a {
  color: #333;
  text-decoration: none;
}

.nav-links a.router-link-active {
  font-weight: 600;
}

.account-button {
  padding: 8px 14px;
  border: 1px solid #333;
  border-radius: 999px;
  font-weight: 600;
}

.cart-button {
  position: relative;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  padding: 8px 12px;
  border: 1px solid #333;
  border-radius: 999px;
  min-width: 44px;
}

.cart-icon {
  width: 20px;
  height: 20px;
  display: block;
}

.cart-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  background: #ff6b00;
  color: #fff;
  border-radius: 999px;
  padding: 2px 6px;
  font-size: 12px;
  font-weight: 600;
  line-height: 1;
}

.main {
  padding: 16px;
}
</style>
