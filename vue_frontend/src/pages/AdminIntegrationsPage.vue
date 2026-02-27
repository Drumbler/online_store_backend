<template>
  <section class="page">
    <header class="heading">
      <div>
        <h1>Integrations</h1>
        <p>Configure payment and shipping providers.</p>
      </div>
    </header>

    <p v-if="toast" class="toast" :class="{ error: toastType === 'error' }">{{ toast }}</p>
    <p v-if="error" class="error">{{ error }}</p>

    <div class="tabs">
      <button :class="{ active: activeKind === 'payment' }" :disabled="busy" @click="switchKind('payment')">
        Payments
      </button>
      <button :class="{ active: activeKind === 'shipping' }" :disabled="busy" @click="switchKind('shipping')">
        Shipping
      </button>
    </div>

    <div v-if="loadingProviders" class="loading">Loading providers...</div>

    <div v-else class="layout">
      <aside class="providers">
        <button
          v-for="provider in providersForKind"
          :key="provider.id"
          class="provider-item"
          :class="{ active: selectedProviderId === provider.id }"
          :disabled="busy"
          @click="selectProvider(provider.id)"
        >
          <strong>{{ provider.title }}</strong>
          <span v-if="provider.description">{{ provider.description }}</span>
        </button>
      </aside>

      <section class="panel" v-if="selectedProvider">
        <h2>{{ selectedProvider.title }}</h2>

        <div v-if="loadingConfig" class="loading">Loading configuration...</div>

        <form v-else class="form" @submit.prevent="saveConfig">
          <label class="field checkbox">
            <input v-model="form.enabled" type="checkbox" :disabled="busy" />
            <span>Enabled</span>
          </label>

          <label class="field checkbox">
            <input v-model="form.is_sandbox" type="checkbox" :disabled="busy" />
            <span>Sandbox mode</span>
          </label>

          <label class="field">
            <span>Display name</span>
            <input v-model="form.display_name" type="text" :disabled="busy" />
          </label>

          <div v-for="field in selectedProvider.fields_schema" :key="`${field.group || 'credentials'}:${field.name}`" class="field-block">
            <label v-if="field.type !== 'boolean'" class="field">
              <span>{{ field.label || field.name }}</span>

              <template v-if="field.type === 'select'">
                <select
                  :value="getFieldValue(field)"
                  :disabled="busy"
                  @change="setFieldValue(field, ($event.target as HTMLSelectElement).value)"
                >
                  <option v-for="option in field.options || []" :key="String(option.value)" :value="option.value">
                    {{ option.label }}
                  </option>
                </select>
              </template>

              <template v-else-if="field.type === 'number'">
                <input
                  :value="getFieldValue(field)"
                  type="number"
                  :disabled="busy"
                  @input="setFieldValue(field, Number(($event.target as HTMLInputElement).value))"
                />
              </template>

              <template v-else-if="field.type === 'password'">
                <div v-if="isStoredSecret(field) && !isReplacingSecret(field)" class="secret-row">
                  <span class="masked">******</span>
                  <button type="button" :disabled="busy" @click="setReplaceSecret(field, true)">
                    Replace secret
                  </button>
                </div>
                <div v-else class="secret-row">
                  <input
                    :value="getFieldValue(field)"
                    type="password"
                    :placeholder="isStoredSecret(field) ? 'Leave empty to keep existing' : ''"
                    :disabled="busy"
                    @input="setFieldValue(field, ($event.target as HTMLInputElement).value)"
                  />
                  <button
                    v-if="isStoredSecret(field)"
                    type="button"
                    :disabled="busy"
                    @click="cancelReplaceSecret(field)"
                  >
                    Keep existing
                  </button>
                </div>
              </template>

              <template v-else>
                <input
                  :value="getFieldValue(field)"
                  type="text"
                  :disabled="busy"
                  @input="setFieldValue(field, ($event.target as HTMLInputElement).value)"
                />
              </template>
            </label>

            <label v-else class="field checkbox">
              <input
                :checked="Boolean(getFieldValue(field))"
                type="checkbox"
                :disabled="busy"
                @change="setFieldValue(field, ($event.target as HTMLInputElement).checked)"
              />
              <span>{{ field.label || field.name }}</span>
            </label>

            <p v-if="fieldError(field)" class="field-error">{{ fieldError(field) }}</p>
          </div>

          <div class="actions">
            <button type="submit" :disabled="busy">Save</button>
            <button type="button" :disabled="busy || !configSaved" @click="testConnection">Test connection</button>
          </div>
        </form>
      </section>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { adminApiClient } from "../api/adminClient";

type Kind = "payment" | "shipping";

type ProviderField = {
  name: string;
  label?: string;
  type: "text" | "password" | "boolean" | "number" | "select";
  required?: boolean;
  group?: "credentials" | "settings";
  options?: Array<{ label: string; value: string | number | boolean }>;
};

type Provider = {
  id: string;
  title: string;
  description?: string;
  fields_schema: ProviderField[];
};

type ConfigResponse = {
  id: number | null;
  kind: Kind;
  provider_id: string;
  enabled: boolean;
  is_sandbox: boolean;
  display_name: string;
  credentials: Record<string, any>;
  settings: Record<string, any>;
};

const providers = ref<Record<Kind, Provider[]>>({ payment: [], shipping: [] });
const activeKind = ref<Kind>("payment");
const selectedProviderId = ref<string>("");

const loadingProviders = ref(false);
const loadingConfig = ref(false);
const saving = ref(false);
const testing = ref(false);
const error = ref<string | null>(null);
const toast = ref<string | null>(null);
const toastType = ref<"ok" | "error">("ok");

const configSaved = ref(false);
const fieldErrors = ref<Record<string, string>>({});

const form = ref({
  enabled: false,
  is_sandbox: true,
  display_name: "",
  credentials: {} as Record<string, any>,
  settings: {} as Record<string, any>
});

const storedSecrets = ref<Record<string, boolean>>({});
const replaceSecrets = ref<Record<string, boolean>>({});

const busy = computed(() => loadingProviders.value || loadingConfig.value || saving.value || testing.value);
const providersForKind = computed(() => providers.value[activeKind.value] || []);
const selectedProvider = computed(() =>
  providersForKind.value.find((provider) => provider.id === selectedProviderId.value) || null
);

const showToast = (message: string, type: "ok" | "error" = "ok") => {
  toastType.value = type;
  toast.value = message;
  window.setTimeout(() => {
    if (toast.value === message) {
      toast.value = null;
    }
  }, 3000);
};

const keyForField = (field: ProviderField) => `${field.group || "credentials"}.${field.name}`;

const fieldGroup = (field: ProviderField) => field.group || "credentials";

const getFieldValue = (field: ProviderField) => {
  const group = fieldGroup(field);
  if (!(field.name in form.value[group])) {
    form.value[group][field.name] = field.type === "boolean" ? false : "";
  }
  return form.value[group][field.name];
};

const setFieldValue = (field: ProviderField, value: any) => {
  const group = fieldGroup(field);
  form.value[group][field.name] = value;
};

const fieldError = (field: ProviderField) => fieldErrors.value[keyForField(field)] || "";

const isStoredSecret = (field: ProviderField) => storedSecrets.value[keyForField(field)] === true;
const isReplacingSecret = (field: ProviderField) => replaceSecrets.value[keyForField(field)] === true;

const setReplaceSecret = (field: ProviderField, value: boolean) => {
  replaceSecrets.value[keyForField(field)] = value;
};

const cancelReplaceSecret = (field: ProviderField) => {
  const key = keyForField(field);
  replaceSecrets.value[key] = false;
  form.value[fieldGroup(field)][field.name] = "";
};

const populateFormFromConfig = (payload: ConfigResponse) => {
  configSaved.value = Boolean(payload.id);
  form.value.enabled = payload.enabled;
  form.value.is_sandbox = payload.is_sandbox;
  form.value.display_name = payload.display_name || "";
  form.value.credentials = { ...(payload.credentials || {}) };
  form.value.settings = { ...(payload.settings || {}) };
  storedSecrets.value = {};
  replaceSecrets.value = {};

  const schema = selectedProvider.value?.fields_schema || [];
  schema.forEach((field) => {
    if (field.type !== "password") {
      return;
    }
    const group = fieldGroup(field);
    const key = keyForField(field);
    const value = form.value[group][field.name];
    if (value === "******") {
      storedSecrets.value[key] = true;
      replaceSecrets.value[key] = false;
      form.value[group][field.name] = "";
    }
  });
};

const loadProviders = async () => {
  loadingProviders.value = true;
  error.value = null;
  try {
    const response = await adminApiClient.get("/admin/integrations/providers/");
    providers.value = {
      payment: response.data?.payment || [],
      shipping: response.data?.shipping || []
    };

    const first = providers.value[activeKind.value][0];
    if (first) {
      selectedProviderId.value = first.id;
      await loadConfig();
    }
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to load integration providers.";
  } finally {
    loadingProviders.value = false;
  }
};

const loadConfig = async () => {
  if (!selectedProviderId.value) {
    return;
  }
  loadingConfig.value = true;
  fieldErrors.value = {};
  error.value = null;
  try {
    const response = await adminApiClient.get(
      `/admin/integrations/configs/${activeKind.value}/${selectedProviderId.value}/`
    );
    populateFormFromConfig(response.data as ConfigResponse);
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to load integration config.";
  } finally {
    loadingConfig.value = false;
  }
};

const switchKind = async (kind: Kind) => {
  if (activeKind.value === kind) {
    return;
  }
  activeKind.value = kind;
  const first = providers.value[kind]?.[0];
  selectedProviderId.value = first?.id || "";
  if (selectedProviderId.value) {
    await loadConfig();
  }
};

const selectProvider = async (providerId: string) => {
  if (selectedProviderId.value === providerId) {
    return;
  }
  selectedProviderId.value = providerId;
  await loadConfig();
};

const requestPayload = () => {
  const payload = {
    enabled: form.value.enabled,
    is_sandbox: form.value.is_sandbox,
    display_name: form.value.display_name,
    credentials: { ...form.value.credentials },
    settings: { ...form.value.settings }
  };

  const schema = selectedProvider.value?.fields_schema || [];
  schema.forEach((field) => {
    if (field.type !== "password") {
      return;
    }
    const group = fieldGroup(field);
    const key = keyForField(field);
    if (isStoredSecret(field) && !isReplacingSecret(field)) {
      payload[group][field.name] = "******";
    }
  });
  return payload;
};

const applyValidationErrors = (data: Record<string, any>) => {
  fieldErrors.value = {};
  Object.entries(data || {}).forEach(([key, value]) => {
    if (Array.isArray(value) && value.length > 0) {
      fieldErrors.value[key] = String(value[0]);
    }
  });
};

const saveConfig = async () => {
  if (!selectedProviderId.value) {
    return;
  }
  saving.value = true;
  error.value = null;
  fieldErrors.value = {};
  try {
    const response = await adminApiClient.put(
      `/admin/integrations/configs/${activeKind.value}/${selectedProviderId.value}/`,
      requestPayload()
    );
    populateFormFromConfig(response.data as ConfigResponse);
    showToast("Configuration saved.");
  } catch (err: any) {
    const data = err?.response?.data;
    if (data && typeof data === "object") {
      applyValidationErrors(data);
    }
    error.value = data?.detail || "Failed to save configuration.";
    showToast(error.value, "error");
  } finally {
    saving.value = false;
  }
};

const testConnection = async () => {
  if (!selectedProviderId.value || !configSaved.value) {
    return;
  }
  testing.value = true;
  error.value = null;
  try {
    const response = await adminApiClient.post(
      `/admin/integrations/configs/${activeKind.value}/${selectedProviderId.value}/test/`
    );
    const ok = Boolean(response.data?.ok);
    const message = response.data?.message || (ok ? "Connection OK" : "Connection failed");
    showToast(message, ok ? "ok" : "error");
  } catch (err: any) {
    const message = err?.response?.data?.detail || "Failed to test connection.";
    error.value = message;
    showToast(message, "error");
  } finally {
    testing.value = false;
  }
};

onMounted(async () => {
  await loadProviders();
});
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.heading h1 {
  margin: 0;
}

.heading p {
  margin: 4px 0 0;
  color: #6b5a45;
}

.tabs {
  display: inline-flex;
  gap: 8px;
}

.tabs button {
  border: 1px solid #d0c1aa;
  background: #fff;
  padding: 8px 12px;
  border-radius: 8px;
}

.tabs button.active {
  background: #f0e7d7;
  font-weight: 600;
}

.layout {
  display: grid;
  grid-template-columns: 260px 1fr;
  gap: 16px;
}

.providers {
  border: 1px solid #d6cbb8;
  background: #fff;
  padding: 10px;
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.provider-item {
  border: 1px solid #e2d7c4;
  background: #fff;
  text-align: left;
  padding: 10px;
  border-radius: 8px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.provider-item span {
  color: #7a6a55;
  font-size: 13px;
}

.provider-item.active {
  border-color: #7a6242;
  background: #f8f2e7;
}

.panel {
  border: 1px solid #d6cbb8;
  background: #fff;
  padding: 16px;
}

.panel h2 {
  margin: 0 0 12px;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field.checkbox {
  flex-direction: row;
  align-items: center;
  gap: 8px;
}

.field-block {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.field input,
.field select {
  min-height: 34px;
}

.secret-row {
  display: flex;
  gap: 8px;
  align-items: center;
}

.masked {
  padding: 8px 10px;
  border: 1px solid #d8ccb8;
  background: #f8f2e7;
}

.actions {
  display: flex;
  gap: 8px;
  margin-top: 8px;
}

.toast {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid #bfe3bf;
  background: #e7f7e7;
}

.toast.error {
  border-color: #f2b3b3;
  background: #ffe1e1;
}

.error {
  margin: 0;
  padding: 10px 12px;
  border: 1px solid #f2b3b3;
  background: #ffe1e1;
  color: #8d2f2f;
}

.field-error {
  margin: 0;
  color: #9f3030;
  font-size: 13px;
}

.loading {
  color: #5f4f3f;
}

@media (max-width: 960px) {
  .layout {
    grid-template-columns: 1fr;
  }
}
</style>
