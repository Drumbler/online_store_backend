<template>
  <section class="page bg-app text-app">
    <h1>Подтверждение эл. почты</h1>
    <p v-if="loading" class="state-box">Проверка...</p>
    <p v-else-if="message" :class="['state-box', success ? 'success' : 'error']">
      {{ message }}
    </p>
    <router-link to="/account">Назад в личный кабинет</router-link>
  </section>
</template>

<script setup lang="ts">
/** Логика страницы и обработчики UI состояния. */
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { verifyEmailToken } from "../api/user";

const route = useRoute();
const loading = ref(true);
const message = ref<string | null>(null);
const success = ref(false);

onMounted(async () => {
  const token = route.query.token;
  if (!token || typeof token !== "string") {
    message.value = "Отсутствует токен подтверждения.";
    success.value = false;
    loading.value = false;
    return;
  }

  try {
    await verifyEmailToken({ token });
    message.value = "Эл. почта успешно подтверждена.";
    success.value = true;
  } catch (err: any) {
    const detail = err?.response?.data?.detail;
    message.value = detail || "Не удалось подтвердить эл. почту.";
    success.value = false;
  } finally {
    loading.value = false;
  }
});
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
  max-width: 520px;
}

</style>
