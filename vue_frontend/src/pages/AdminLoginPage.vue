<template>
  <section class="page">
    <div class="card">
      <h1>Admin Login</h1>
      <p class="hint">Enter the admin API token to continue.</p>
      <form class="form" @submit.prevent="submit">
        <label class="field">
          <span>Admin token</span>
          <input v-model="token" type="password" required />
        </label>
        <button type="submit">Sign in</button>
        <p v-if="error" class="error">{{ error }}</p>
      </form>
    </div>
  </section>
</template>

<script setup lang="ts">
import { ref } from "vue";
import { useRoute, useRouter } from "vue-router";
import { useAdminAuthStore } from "../stores/adminAuth";

const token = ref("");
const error = ref<string | null>(null);
const router = useRouter();
const route = useRoute();
const adminAuthStore = useAdminAuthStore();

const submit = async () => {
  if (!token.value.trim()) {
    error.value = "Token is required.";
    return;
  }
  error.value = null;
  adminAuthStore.setToken(token.value.trim());
  const target = (route.query.redirect as string) || "/admin/products";
  await router.push(target);
};
</script>

<style scoped>
.page {
  min-height: 100vh;
  display: grid;
  place-items: center;
  background: radial-gradient(circle at top, #f6efe1, #efe6d4);
  padding: 24px;
}

.card {
  width: min(420px, 100%);
  background: #fff;
  padding: 24px;
  border: 1px solid #e2d5be;
  box-shadow: 0 18px 40px rgba(75, 60, 47, 0.1);
}

.hint {
  color: #6f5f4c;
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

.error {
  color: #b11e1e;
  margin: 0;
}
</style>
