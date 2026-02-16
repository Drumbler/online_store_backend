<template>
  <section class="page">
    <header class="heading">
      <div>
        <h1>Users</h1>
        <p>Manage access and status for store users.</p>
      </div>
      <div class="controls">
        <label class="field">
          <span>Page size</span>
          <select v-model.number="pageSize" :disabled="loading">
            <option :value="10">10</option>
            <option :value="20">20</option>
            <option :value="50">50</option>
          </select>
        </label>
      </div>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="loading" class="loading">Loading users...</div>

    <div v-else class="table-wrap">
      <table class="table">
        <thead>
          <tr>
            <th>Username</th>
            <th>Email</th>
            <th>Role</th>
            <th>Status</th>
            <th>Date joined</th>
            <th>Last login</th>
            <th>Actions</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="user in users" :key="user.id">
            <td class="mono">{{ user.username }}</td>
            <td>{{ user.email || "—" }}</td>
            <td>
              <select
                v-model="user.is_staff"
                :disabled="isBlocked(user) || isUpdating(user.id)"
                @change="handleRoleChange(user)"
              >
                <option :value="false">User</option>
                <option :value="true">Admin</option>
              </select>
            </td>
            <td>
              <select
                v-model="user.is_active"
                :disabled="isBlocked(user) || isUpdating(user.id)"
                @change="handleStatusChange(user)"
              >
                <option :value="true">Active</option>
                <option :value="false">Blocked</option>
              </select>
            </td>
            <td>{{ formatDate(user.date_joined) }}</td>
            <td>{{ formatDate(user.last_login) }}</td>
            <td class="actions">
              <span v-if="user.is_superuser" class="badge">Superuser</span>
              <span v-else-if="isSelf(user)" class="badge">You</span>
              <span v-else class="badge subtle">Editable</span>
            </td>
          </tr>
          <tr v-if="users.length === 0">
            <td colspan="7" class="empty">No users found.</td>
          </tr>
        </tbody>
      </table>
    </div>

    <footer class="pagination">
      <button type="button" :disabled="loading || page <= 1" @click="changePage(page - 1)">
        Previous
      </button>
      <span>Page {{ page }} of {{ totalPages }}</span>
      <button
        type="button"
        :disabled="loading || page >= totalPages"
        @click="changePage(page + 1)"
      >
        Next
      </button>
    </footer>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";

import { adminApiClient } from "../api/adminClient";
import { useAuthStore } from "../stores/auth";

type AdminUser = {
  id: number;
  username: string;
  email?: string | null;
  name?: string | null;
  is_staff: boolean;
  is_superuser: boolean;
  is_active: boolean;
  date_joined: string;
  last_login: string | null;
};

const authStore = useAuthStore();
const users = ref<AdminUser[]>([]);
const loading = ref(false);
const error = ref<string | null>(null);
const page = ref(1);
const pageSize = ref(20);
const total = ref(0);
const updatingIds = ref<Set<number>>(new Set());

const totalPages = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)));

const isUpdating = (id: number) => updatingIds.value.has(id);

const isSelf = (user: AdminUser) =>
  authStore.user ? String(authStore.user.id) === String(user.id) : false;

const isBlocked = (user: AdminUser) => user.is_superuser || isSelf(user);

const formatDate = (value: string | null) => {
  if (!value) return "—";
  const parsed = new Date(value);
  if (Number.isNaN(parsed.getTime())) return value;
  return parsed.toLocaleString();
};

const loadUsers = async () => {
  loading.value = true;
  error.value = null;
  try {
    const response = await adminApiClient.get("/admin/users/", {
      params: {
        page: page.value,
        page_size: pageSize.value
      }
    });
    users.value = response.data.results || [];
    total.value = response.data.pagination?.total ?? users.value.length;
  } catch (err) {
    console.error(err);
    error.value = "Failed to load users. Please try again.";
  } finally {
    loading.value = false;
  }
};

const changePage = async (nextPage: number) => {
  page.value = nextPage;
  await loadUsers();
};

const updateUser = async (user: AdminUser, payload: Partial<AdminUser>, revert: () => void) => {
  updatingIds.value.add(user.id);
  error.value = null;
  try {
    const response = await adminApiClient.patch(`/admin/users/${user.id}/`, payload);
    const updated = response.data;
    user.is_staff = updated.is_staff;
    user.is_active = updated.is_active;
    user.name = updated.name;
  } catch (err) {
    console.error(err);
    revert();
    error.value = "Update failed. Changes were reverted.";
  } finally {
    updatingIds.value.delete(user.id);
  }
};

const handleRoleChange = (user: AdminUser) => {
  const previous = !user.is_staff;
  updateUser(user, { is_staff: user.is_staff }, () => {
    user.is_staff = previous;
  });
};

const handleStatusChange = (user: AdminUser) => {
  const previous = !user.is_active;
  updateUser(user, { is_active: user.is_active }, () => {
    user.is_active = previous;
  });
};

onMounted(async () => {
  if (!authStore.user) {
    await authStore.fetchMe();
  }
  await loadUsers();
});
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.heading p {
  color: #6f5f4c;
}

.controls {
  display: flex;
  gap: 12px;
  align-items: center;
}

.field {
  display: flex;
  flex-direction: column;
  gap: 6px;
  font-size: 14px;
}

.error {
  color: #b11e1e;
  margin: 0;
}

.loading {
  padding: 16px;
  border: 1px dashed #c6b59a;
  background: #fffdf8;
}

.table-wrap {
  overflow-x: auto;
  background: #fffdf8;
  border: 1px solid #e2d5be;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th,
.table td {
  padding: 12px;
  border-bottom: 1px solid #eadfc9;
  text-align: left;
  white-space: nowrap;
}

.table th {
  background: #f3ead8;
  font-weight: 600;
}

.table tr:last-child td {
  border-bottom: none;
}

.mono {
  font-family: "Courier New", Courier, monospace;
}

.actions {
  display: flex;
  gap: 8px;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: #efe4cf;
  color: #4b3c2f;
  font-size: 12px;
}

.badge.subtle {
  background: #f6efe1;
  color: #6f5f4c;
}

.empty {
  text-align: center;
  color: #6f5f4c;
}

.pagination {
  display: flex;
  align-items: center;
  gap: 12px;
}

.pagination button {
  padding: 8px 12px;
  border: 1px solid #c6b59a;
  background: #f6efe1;
  cursor: pointer;
}

.pagination button:disabled {
  cursor: not-allowed;
  opacity: 0.6;
}
</style>
