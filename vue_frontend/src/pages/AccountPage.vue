<template>
  <section class="page bg-app text-app">
    <h1>Личный кабинет</h1>

    <div v-if="loading" class="state-box">Профиль загружается...</div>
    <div v-else>
      <div class="card surface-card">
        <h2>Имя в профиле</h2>
        <div class="field">
          <label for="display-name">Имя в профиле</label>
          <input id="display-name" v-model="nameInput" type="text" placeholder="Введите имя" />
        </div>
        <div class="actions">
          <button type="button" class="btn btn-primary" :disabled="nameSaving" @click="saveName">Сохранить</button>
          <span v-if="nameStatus" class="state-box success">{{ nameStatus }}</span>
          <span v-if="nameError" class="state-box error">{{ nameError }}</span>
        </div>
      </div>

      <div class="card surface-card">
        <h2>Эл. почта</h2>
        <div class="field">
          <label for="email">Эл. почта</label>
          <input
            id="email"
            v-model="emailInput"
            type="email"
            :placeholder="emailPlaceholder"
            :disabled="emailInputDisabled"
          />
        </div>
        <p v-if="emailHelperText" class="helper">{{ emailHelperText }}</p>
        <p v-if="emailVerifiedLabel" class="helper success">Подтверждено</p>
        <div class="actions">
          <button type="button" class="btn btn-neutral" :disabled="emailChangeDisabled" @click="enableEmailEditing">
            Изменить
          </button>
          <button type="button" class="btn btn-primary" :disabled="emailConfirmDisabled" @click="confirmEmail">
            Подтвердить
          </button>
        </div>
        <div class="status-group">
          <span v-if="emailStatus" class="state-box success">{{ emailStatus }}</span>
          <span v-if="emailError" class="state-box error">{{ emailError }}</span>
        </div>
      </div>

      <div class="card surface-card">
        <h2>Смена пароля</h2>
        <form class="form" @submit.prevent="submitPassword">
          <label class="field">
            <span>Текущий пароль</span>
            <input v-model="currentPassword" type="password" required />
          </label>
          <label class="field">
            <span>Новый пароль</span>
            <input v-model="newPassword" type="password" required />
          </label>
          <label class="field">
            <span>Повтор нового пароля</span>
            <input v-model="newPasswordConfirm" type="password" required />
          </label>
          <div class="actions">
            <button type="submit" class="btn btn-primary" :disabled="passwordSaving">Изменить пароль</button>
          </div>
        </form>
        <div class="status-group">
          <span v-if="passwordStatus" class="state-box success">{{ passwordStatus }}</span>
          <span v-if="passwordError" class="state-box error">{{ passwordError }}</span>
        </div>
      </div>
      <div class="card surface-card">
        <h2>Сессия</h2>
        <div class="actions">
          <button type="button" class="btn btn-outline danger-button" @click="handleLogout">Выйти</button>
        </div>
        <div class="status-group">
          <span v-if="logoutStatus" class="state-box success">{{ logoutStatus }}</span>
          <span v-if="logoutError" class="state-box error">{{ logoutError }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
/** Логика страницы и обработчики UI состояния. */
import { computed, onMounted, ref } from "vue";
import { useRouter } from "vue-router";
import {
  changePassword,
  fetchAccountProfile,
  requestEmailVerification,
  setAccountEmail,
  updateAccountName
} from "../api/user";
import { useAuthStore } from "../stores/auth";

const loading = ref(true);
const nameSaving = ref(false);
const emailSaving = ref(false);
const passwordSaving = ref(false);

const nameStatus = ref<string | null>(null);
const emailStatus = ref<string | null>(null);
const passwordStatus = ref<string | null>(null);

const nameError = ref<string | null>(null);
const emailError = ref<string | null>(null);
const passwordError = ref<string | null>(null);

const profile = ref<{ id: number; username: string; name: string | null; email: string | null; email_verified: boolean } | null>(
  null
);

const nameInput = ref("");
const emailInput = ref("");
const editingEmail = ref(false);

const currentPassword = ref("");
const newPassword = ref("");
const newPasswordConfirm = ref("");
const logoutStatus = ref<string | null>(null);
const logoutError = ref<string | null>(null);

const router = useRouter();
const authStore = useAuthStore();

const loadProfile = async () => {
  loading.value = true;
  try {
    const response = await fetchAccountProfile();
    profile.value = response.data;
    nameInput.value = response.data.name || "";
    emailInput.value = response.data.email || "";
    editingEmail.value = false;
  } finally {
    loading.value = false;
  }
};

onMounted(loadProfile);

const savedEmail = computed(() => profile.value?.email || "");
const emailVerified = computed(() => Boolean(profile.value?.email_verified));
const hasSavedEmail = computed(() => Boolean(savedEmail.value));
const emailDirty = computed(() => emailInput.value.trim() !== savedEmail.value);

const emailInputDisabled = computed(() => emailVerified.value && !editingEmail.value);
const emailPlaceholder = computed(() => (hasSavedEmail.value ? "" : "Укажите эл. почту"));

const emailHelperText = computed(() => {
  if (!hasSavedEmail.value) {
    return "Добавьте эл. почту, чтобы включить расширенные возможности профиля";
  }
  if (!emailVerified.value) {
    return "Эл. почта не подтверждена. Подтвердите адрес.";
  }
  return "";
});

const emailVerifiedLabel = computed(() => emailVerified.value && hasSavedEmail.value && !editingEmail.value);

const emailChangeDisabled = computed(() => !hasSavedEmail.value || emailSaving.value);
const emailConfirmDisabled = computed(() => {
  if (emailSaving.value) return true;
  if (emailVerified.value && !editingEmail.value) return true;
  return !emailInput.value.trim();
});

const extractError = (err: any, fallback: string) => {
  const data = err?.response?.data;
  if (!data) return fallback;
  if (typeof data.detail === "string") return data.detail;
  const firstKey = Object.keys(data)[0];
  if (firstKey && Array.isArray(data[firstKey])) {
    return data[firstKey][0];
  }
  return fallback;
};

const saveName = async () => {
  nameSaving.value = true;
  nameStatus.value = null;
  nameError.value = null;
  try {
    const response = await updateAccountName({ name: nameInput.value || "" });
    profile.value = response.data;
    nameStatus.value = "Сохранено.";
  } catch (err: any) {
    nameError.value = extractError(err, "Не удалось обновить имя в профиле.");
  } finally {
    nameSaving.value = false;
  }
};

const enableEmailEditing = () => {
  if (!hasSavedEmail.value) return;
  editingEmail.value = true;
  if (!emailInput.value) {
    emailInput.value = savedEmail.value;
  }
};

const confirmEmail = async () => {
  if (!emailInput.value.trim()) return;
  emailSaving.value = true;
  emailStatus.value = null;
  emailError.value = null;
  try {
    if (!hasSavedEmail.value || emailDirty.value) {
      const response = await setAccountEmail({ email: emailInput.value.trim() });
      profile.value = response.data;
      editingEmail.value = false;
      emailStatus.value = "Эл. почта сохранена. Подтвердите адрес.";
      return;
    }

    if (!emailVerified.value) {
      await requestEmailVerification();
      emailStatus.value = "Письмо со ссылкой для подтверждения отправлено.";
    }
  } catch (err: any) {
    emailError.value = extractError(err, "Не удалось выполнить действие с эл. почтой.");
  } finally {
    emailSaving.value = false;
  }
};

const submitPassword = async () => {
  passwordSaving.value = true;
  passwordStatus.value = null;
  passwordError.value = null;
  try {
    await changePassword({
      current_password: currentPassword.value,
      new_password: newPassword.value,
      new_password_confirm: newPasswordConfirm.value
    });
    passwordStatus.value = "Пароль обновлен.";
    currentPassword.value = "";
    newPassword.value = "";
    newPasswordConfirm.value = "";
  } catch (err: any) {
    passwordError.value = extractError(err, "Не удалось изменить пароль.");
  } finally {
    passwordSaving.value = false;
  }
};

const handleLogout = async () => {
  logoutStatus.value = null;
  logoutError.value = null;
  try {
    await authStore.logout();
    logoutStatus.value = "Вы вышли из аккаунта.";
    await router.push("/");
  } catch {
    logoutError.value = "Не удалось выйти из аккаунта.";
  }
};
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 20px;
  max-width: 720px;
}

.card {
  padding: 16px;
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.actions {
  display: flex;
  gap: 12px;
  align-items: center;
  flex-wrap: wrap;
}

.status-group {
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.helper {
  color: var(--muted);
  margin: 0;
}

.helper.success {
  color: color-mix(in srgb, #2f8f52 75%, var(--text));
}

.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.danger-button {
  border-color: color-mix(in srgb, #d13b3b 45%, var(--border));
  color: color-mix(in srgb, #d13b3b 78%, var(--text));
  background: color-mix(in srgb, #d13b3b 12%, transparent);
}
</style>
