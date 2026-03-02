<template>
  <section class="page bg-app text-app">
    <h1>Вход</h1>

    <form class="form" @submit.prevent="submit">
      <label class="field">
        <span>Имя пользователя или эл. почта</span>
        <input v-model="usernameOrEmail" type="text" required />
      </label>
      <label class="field">
        <span>Пароль</span>
        <input v-model="password" type="password" required />
      </label>
      <button type="submit" class="btn btn-primary" :disabled="loading">Войти</button>
    </form>

    <p v-if="error" class="state-box error">{{ error }}</p>
  </section>
</template>

<script setup lang="ts">
/** Логика страницы и обработчики UI состояния. */
import { ref } from "vue";
import { useRoute } from "vue-router";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const router = useRouter();
const route = useRoute();

const usernameOrEmail = ref("");
const password = ref("");
const loading = ref(false);
const error = ref<string | null>(null);

const submit = async () => {
  loading.value = true;
  error.value = null;
  try {
    await authStore.login({
      username_or_email: usernameOrEmail.value,
      password: password.value
    });
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/";
    await router.push(redirect);
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Не удалось выполнить вход.";
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 420px;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

</style>
