<template>
  <section class="page">
    <h1>Sign in</h1>

    <form class="form" @submit.prevent="submit">
      <label class="field">
        <span>Username or email</span>
        <input v-model="usernameOrEmail" type="text" required />
      </label>
      <label class="field">
        <span>Password</span>
        <input v-model="password" type="password" required />
      </label>
      <button type="submit" :disabled="loading">Login</button>
    </form>

    <p v-if="error" class="status error">{{ error }}</p>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRouter } from "vue-router";
import { useAuthStore } from "../stores/auth";

const authStore = useAuthStore();
const router = useRouter();

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
    await router.push("/");
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Login failed.";
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

.status {
  padding: 12px;
  background: #fff6d8;
  border: 1px solid #f0dca0;
}

.status.error {
  background: #ffe1e1;
  border-color: #f2b3b3;
}
</style>
