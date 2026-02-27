<template>
  <section class="page bg-app text-app">
    <h1>Verify email</h1>
    <p v-if="loading" class="state-box">Verifying...</p>
    <p v-else-if="message" :class="['state-box', success ? 'success' : 'error']">
      {{ message }}
    </p>
    <router-link to="/account">Back to account</router-link>
  </section>
</template>

<script setup lang="ts">
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
    message.value = "Missing verification token.";
    success.value = false;
    loading.value = false;
    return;
  }

  try {
    await verifyEmailToken({ token });
    message.value = "Email verified successfully.";
    success.value = true;
  } catch (err: any) {
    const detail = err?.response?.data?.detail;
    message.value = detail || "Email verification failed.";
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
