<template>
  <section class="page bg-app text-app">
    <h1>Регистрация</h1>

    <form class="form" @submit.prevent="submit">
      <label class="field">
        <span>Имя пользователя</span>
        <input v-model="username" type="text" required />
      </label>
      <label class="field">
        <span>Эл. почта (необязательно)</span>
        <input v-model="email" type="email" />
      </label>
      <label class="field">
        <span>Пароль</span>
        <input v-model="password" type="password" required />
      </label>
      <button type="submit" class="btn btn-primary" :disabled="loading">Зарегистрироваться</button>
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

const username = ref("");
const email = ref("");
const password = ref("");
const loading = ref(false);
const error = ref<string | null>(null);

const submit = async () => {
  loading.value = true;
  error.value = null;
  try {
    await authStore.register({
      username: username.value,
      email: email.value || undefined,
      password: password.value
    });
    const redirect = typeof route.query.redirect === "string" ? route.query.redirect : "/";
    await router.push(redirect);
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Не удалось зарегистрироваться.";
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
