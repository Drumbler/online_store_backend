<template>
  <div class="app" :style="storefrontStyle" :class="{ 'storefront-dark': isStorefrontDark }">
    <header v-if="showPublicNav" class="navbar">
      <nav class="nav-links" aria-label="Навигация магазина">
        <div class="nav-left">
          <RouterLink to="/" class="brand-link" :aria-label="`${shopName} — главная`">
            <img v-if="logoUrl" :src="logoUrl" alt="Логотип магазина" class="shop-logo" />
            <span v-else class="shop-name">{{ shopName }}</span>
          </RouterLink>
        </div>

        <div class="nav-center">
          <div class="nav-center-links">
            <RouterLink to="/" class="nav-link">Каталог</RouterLink>
            <RouterLink to="/categories" class="nav-link">Категории</RouterLink>
            <RouterLink :to="ordersRoutePath" class="nav-link">
              {{ isLoggedIn ? "Мои заказы" : "Поиск заказа" }}
            </RouterLink>
            <RouterLink v-if="isAdmin" to="/admin" class="nav-link">Админка</RouterLink>
            <RouterLink v-if="!isLoggedIn" to="/login" class="nav-link">Войти</RouterLink>
            <RouterLink v-if="!isLoggedIn" to="/register" class="nav-link">Регистрация</RouterLink>
          </div>
        </div>

        <div class="nav-right">
          <RouterLink to="/cart" class="icon-btn" aria-label="Корзина" title="Корзина">
            <svg
              class="icon-svg"
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

          <RouterLink
            v-if="isLoggedIn"
            to="/account"
            class="icon-btn"
            aria-label="Профиль"
            title="Личный кабинет"
          >
            <svg
              class="icon-svg"
              viewBox="0 0 24 24"
              role="img"
              aria-hidden="true"
              focusable="false"
            >
              <path
                d="M12 12a5 5 0 1 0-5-5 5 5 0 0 0 5 5zm0 2c-4.33 0-8 2.17-8 5v1h16v-1c0-2.83-3.67-5-8-5z"
                fill="currentColor"
              />
            </svg>
          </RouterLink>
        </div>
      </nav>
    </header>

    <section v-if="showPublicNav && belowHeaderBanners.length" class="top-banners">
      <a
        v-for="banner in belowHeaderBanners"
        :key="banner.id"
        class="banner-link"
        :href="banner.link_url"
        target="_blank"
        rel="noopener noreferrer"
      >
        <img class="banner-image" :src="banner.image_url" alt="Баннер магазина" />
      </a>
    </section>

    <main class="main">
      <RouterView />
    </main>

    <footer v-if="showPublicNav" class="store-footer">
      <RouterLink to="/" class="footer-brand">{{ shopName }}</RouterLink>
      <span class="footer-copy">Товары для повседневных задач</span>
    </footer>
  </div>
</template>

<script setup lang="ts">
/** Логика страницы и обработчики UI состояния. */
import { computed, onMounted, watch } from "vue";
import { useRoute } from "vue-router";

import { useCartStore } from "./stores/cart";
import { useAuthStore } from "./stores/auth";
import { useAppearanceStore } from "./stores/appearance";

const cartStore = useCartStore();
const authStore = useAuthStore();
const appearanceStore = useAppearanceStore();
const route = useRoute();

const shopName = "Интернет-магазин";
const cartCount = computed(() => cartStore.cartCount);
const logoUrl = computed(() => appearanceStore.payload.logo_url || "");
const isLoggedIn = computed(() => Boolean(authStore.token));
const ordersRoutePath = computed(() => (isLoggedIn.value ? "/orders" : "/orders/find"));
const isAdmin = computed(
  () =>
    Boolean(
      authStore.user?.is_admin || authStore.user?.is_staff || authStore.user?.is_superuser
    )
);
const showPublicNav = computed(() => !route.path.startsWith("/admin"));

const belowHeaderBanners = computed(() => appearanceStore.belowHeaderBanners);

const storefrontStyle = computed(() => {
  if (!showPublicNav.value) {
    return {};
  }
  return appearanceStore.storefrontCssVars;
});

const isStorefrontDark = computed(
  () => showPublicNav.value && appearanceStore.payload.theme_mode === "dark"
);

const ensureAppearanceLoaded = async () => {
  if (!showPublicNav.value) {
    return;
  }
  await appearanceStore.loadPublishedAppearance();
};

watch(
  () => route.path,
  async () => {
    await ensureAppearanceLoaded();
  }
);

onMounted(async () => {
  await ensureAppearanceLoaded();
});
</script>

<style scoped>
.app {
  min-height: 100vh;
  display: flex;
  flex-direction: column;
  background-color: var(--bg);
  color: var(--text);
}

.navbar {
  padding: 14px 16px;
  border-bottom: 1px solid var(--border);
  background: var(--surface);
  box-shadow: var(--shadow);
}

.nav-links {
  max-width: 1280px;
  margin: 0 auto;
  display: flex;
  align-items: center;
  gap: 12px;
}

.nav-left,
.nav-right {
  flex: 0 0 220px;
  display: flex;
  align-items: center;
}

.nav-right {
  justify-content: flex-end;
  gap: 10px;
}

.nav-center {
  flex: 1;
  display: flex;
  justify-content: center;
}

.nav-center-links {
  display: flex;
  gap: 10px;
  align-items: center;
  justify-content: center;
  flex-wrap: wrap;
}

.brand-link {
  display: inline-flex;
  align-items: center;
  text-decoration: none;
  color: inherit;
}

.shop-logo {
  width: 52px;
  height: 52px;
  object-fit: cover;
  border: 1px solid var(--border);
  border-radius: 12px;
}

.shop-name {
  font-size: 1.1rem;
  font-weight: 800;
  letter-spacing: 0.01em;
  white-space: nowrap;
}

.nav-link {
  color: var(--text);
  text-decoration: none;
  font-weight: 500;
  padding: 7px 10px;
  border-radius: 10px;
  transition: background-color 0.2s ease, color 0.2s ease;
}

.nav-link.router-link-active {
  color: var(--primary);
  background: color-mix(in srgb, var(--primary) 12%, transparent);
  font-weight: 700;
}

.icon-btn {
  position: relative;
  width: 44px;
  height: 44px;
  display: inline-flex;
  align-items: center;
  justify-content: center;
  border-radius: 999px;
  border: 1px solid var(--border);
  background: var(--surface);
  color: var(--text);
  text-decoration: none;
  transition: border-color 0.2s ease, color 0.2s ease, transform 0.2s ease;
}

.icon-btn:hover {
  border-color: var(--primary);
  color: var(--primary);
  transform: translateY(-1px);
}

.icon-svg {
  width: 20px;
  height: 20px;
  display: block;
}

.cart-badge {
  position: absolute;
  top: -6px;
  right: -6px;
  background: var(--primary);
  color: var(--primary-contrast);
  border-radius: 999px;
  padding: 2px 6px;
  font-size: 12px;
  font-weight: 700;
  line-height: 1;
}

.top-banners {
  display: grid;
  gap: 10px;
  padding: 12px 16px;
}

.banner-link {
  display: block;
  border: 1px solid var(--border);
  border-radius: 12px;
  overflow: hidden;
  background: var(--surface);
  box-shadow: var(--shadow);
}

.banner-image {
  width: 100%;
  max-height: 200px;
  object-fit: cover;
  display: block;
}

.main {
  flex: 1;
  padding: 16px;
}

.store-footer {
  margin-top: auto;
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 12px;
  border-top: 1px solid var(--border);
  background: var(--surface);
  padding: 14px 16px;
  box-shadow: var(--shadow);
}

.footer-brand {
  color: var(--text);
  text-decoration: none;
  font-weight: 800;
}

.footer-copy {
  color: var(--muted);
  font-size: 0.92rem;
}

@media (max-width: 1024px) {
  .nav-left,
  .nav-right {
    flex-basis: 170px;
  }
}

@media (max-width: 760px) {
  .nav-links {
    flex-wrap: wrap;
  }

  .nav-left {
    flex: 1 1 auto;
  }

  .nav-center {
    order: 3;
    flex: 1 1 100%;
    justify-content: flex-start;
  }

  .nav-center-links {
    justify-content: flex-start;
  }

  .nav-right {
    flex: 0 0 auto;
    margin-left: auto;
  }

  .store-footer {
    flex-direction: column;
    align-items: flex-start;
  }
}
</style>
