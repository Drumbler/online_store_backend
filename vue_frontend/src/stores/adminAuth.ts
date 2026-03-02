/** Legacy store админ-токена (сохраняется для обратной совместимости). */
import { defineStore } from "pinia";
import { ref } from "vue";

const ADMIN_TOKEN_KEY = "adminToken";

export const useAdminAuthStore = defineStore("adminAuth", () => {
  const token = ref<string | null>(localStorage.getItem(ADMIN_TOKEN_KEY));

  const setToken = (value: string) => {
    /** Сохраняет admin token в state и localStorage. */
    token.value = value;
    localStorage.setItem(ADMIN_TOKEN_KEY, value);
  };

  const clearToken = () => {
    /** Очищает admin token из state и localStorage. */
    token.value = null;
    localStorage.removeItem(ADMIN_TOKEN_KEY);
  };

  return {
    token,
    setToken,
    clearToken
  };
});
