/**
 * Точка входа SPA:
 * - подключает Pinia и роутер;
 * - поднимает приложение;
 * - при старте пытается восстановить профиль авторизованного пользователя.
 */
import { createApp } from "vue";
import { createPinia } from "pinia";

import App from "./App.vue";
import router from "./router";
import "./style.css";
import { useAuthStore } from "./stores/auth";

const app = createApp(App);
const pinia = createPinia();

app.use(pinia);
app.use(router);

const authStore = useAuthStore(pinia);
// Восстановление сессии, если access token уже есть в localStorage.
authStore.fetchMe();

app.mount("#app");
