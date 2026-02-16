<template>
  <section class="page">
    <h1>Account</h1>

    <div v-if="loading" class="status">Loading profile...</div>
    <div v-else>
      <div class="card">
        <h2>Display name</h2>
        <div class="field">
          <label for="display-name">Display name</label>
          <input id="display-name" v-model="nameInput" type="text" placeholder="Enter your name" />
        </div>
        <div class="actions">
          <button type="button" :disabled="nameSaving" @click="saveName">Save</button>
          <span v-if="nameStatus" class="status success">{{ nameStatus }}</span>
          <span v-if="nameError" class="status error">{{ nameError }}</span>
        </div>
      </div>

      <div class="card">
        <h2>Email</h2>
        <div class="field">
          <label for="email">Email</label>
          <input
            id="email"
            v-model="emailInput"
            type="email"
            :placeholder="emailPlaceholder"
            :disabled="emailInputDisabled"
          />
        </div>
        <p v-if="emailHelperText" class="helper">{{ emailHelperText }}</p>
        <p v-if="emailVerifiedLabel" class="helper success">Verified</p>
        <div class="actions">
          <button type="button" :disabled="emailChangeDisabled" @click="enableEmailEditing">
            Change
          </button>
          <button type="button" :disabled="emailConfirmDisabled" @click="confirmEmail">
            Confirm
          </button>
        </div>
        <div class="status-group">
          <span v-if="emailStatus" class="status success">{{ emailStatus }}</span>
          <span v-if="emailError" class="status error">{{ emailError }}</span>
        </div>
      </div>

      <div class="card">
        <h2>Change password</h2>
        <form class="form" @submit.prevent="submitPassword">
          <label class="field">
            <span>Current password</span>
            <input v-model="currentPassword" type="password" required />
          </label>
          <label class="field">
            <span>New password</span>
            <input v-model="newPassword" type="password" required />
          </label>
          <label class="field">
            <span>Confirm new password</span>
            <input v-model="newPasswordConfirm" type="password" required />
          </label>
          <div class="actions">
            <button type="submit" :disabled="passwordSaving">Change password</button>
          </div>
        </form>
        <div class="status-group">
          <span v-if="passwordStatus" class="status success">{{ passwordStatus }}</span>
          <span v-if="passwordError" class="status error">{{ passwordError }}</span>
        </div>
      </div>
      <div class="card">
        <h2>Session</h2>
        <div class="actions">
          <button type="button" class="danger-button" @click="handleLogout">Logout</button>
        </div>
        <div class="status-group">
          <span v-if="logoutStatus" class="status success">{{ logoutStatus }}</span>
          <span v-if="logoutError" class="status error">{{ logoutError }}</span>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
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
const emailPlaceholder = computed(() => (hasSavedEmail.value ? "" : "Bind your email"));

const emailHelperText = computed(() => {
  if (!hasSavedEmail.value) {
    return "Bind email to enable advanced profile features";
  }
  if (!emailVerified.value) {
    return "Email is not verified. Please confirm.";
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
    nameStatus.value = "Saved.";
  } catch (err: any) {
    nameError.value = extractError(err, "Failed to update display name.");
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
      emailStatus.value = "Email saved. Please confirm to verify.";
      return;
    }

    if (!emailVerified.value) {
      await requestEmailVerification();
      emailStatus.value = "An email has been sent with a verification link.";
    }
  } catch (err: any) {
    emailError.value = extractError(err, "Email action failed.");
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
    passwordStatus.value = "Password updated.";
    currentPassword.value = "";
    newPassword.value = "";
    newPasswordConfirm.value = "";
  } catch (err: any) {
    passwordError.value = extractError(err, "Failed to change password.");
  } finally {
    passwordSaving.value = false;
  }
};

const handleLogout = async () => {
  logoutStatus.value = null;
  logoutError.value = null;
  try {
    await authStore.logout();
    logoutStatus.value = "You have been logged out.";
    await router.push("/");
  } catch {
    logoutError.value = "Failed to log out.";
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
  border: 1px solid #e0e0e0;
  padding: 16px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 12px;
  background: #fff;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.field input {
  padding: 10px;
  border-radius: 6px;
  border: 1px solid #d0d0d0;
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

.status {
  padding: 10px;
  background: #fff6d8;
  border: 1px solid #f0dca0;
  border-radius: 6px;
}

.status.success {
  background: #e8f7e8;
  border-color: #b9e2b9;
}

.status.error {
  background: #ffe1e1;
  border-color: #f2b3b3;
}

.helper {
  color: #6b6b6b;
  margin: 0;
}

.helper.success {
  color: #1a7f37;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.danger-button {
  padding: 8px 14px;
  border-radius: 6px;
  border: 1px solid #c62828;
  background: #ffecec;
  color: #b71c1c;
  font-weight: 600;
}
</style>
