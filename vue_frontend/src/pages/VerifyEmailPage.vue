<template>
  <section class="page">
    <h1>Verify email</h1>
    <p v-if="loading" class="status">Verifying...</p>
    <p v-else-if="message" :class="['status', success ? 'success' : 'error']">
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

.status {
  padding: 12px;
  border-radius: 6px;
  background: #fff6d8;
  border: 1px solid #f0dca0;
}

.status.success {
  background: #e8f7e8;
  border-color: #b9e2b9;
}

.status.error {
  background: #ffe1e1;
  border-color: #f2b3b3;
}
</style>
