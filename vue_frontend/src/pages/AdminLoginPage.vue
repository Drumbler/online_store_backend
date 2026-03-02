<template>
  <section class="page bg-app text-app">
    <div class="card surface-card">
      <h1>Вход в админ-панель</h1>
      <p class="hint">Войдите под учётной записью администратора.</p>
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
        <p v-if="error" class="state-box error">{{ error }}</p>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
/** Логика страницы и обработчики UI состояния. */
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const usernameOrEmail = ref("");
const password = ref("");
const loading = ref(false);
const error = ref<string | null>(null);
const router = useRouter();
const route = useRoute();
const authStore = useAuthStore();

const submit = async () => {
  loading.value = true;
  error.value = null;
  try {
    await authStore.login({
      username_or_email: usernameOrEmail.value.trim(),
      password: password.value
    });
    const isAdmin = Boolean(
      authStore.user?.is_admin || authStore.user?.is_staff || authStore.user?.is_superuser
    );
    if (!isAdmin) {
      await authStore.logout();
      error.value = "Доступ разрешен только администраторам.";
      return;
    }

    const target = (route.query.redirect as string) || "/admin/products";
    await router.push(target);
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Не удалось выполнить вход.";
  } finally {
    loading.value = false;
  }
};
</script>

<style scoped>
.page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  padding: 24px;
}

.card {
  width: min(420px, 100%);
  padding: 24px;
}

.hint {
  color: var(--muted);
  margin-bottom: 16px;
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
