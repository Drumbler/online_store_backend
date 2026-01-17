import { defineStore } from "pinia";
import { ref } from "vue";

const ADMIN_TOKEN_KEY = "adminToken";

export const useAdminAuthStore = defineStore("adminAuth", () => {
  const token = ref<string | null>(localStorage.getItem(ADMIN_TOKEN_KEY));

  const setToken = (value: string) => {
    token.value = value;
    localStorage.setItem(ADMIN_TOKEN_KEY, value);
  };

  const clearToken = () => {
    token.value = null;
    localStorage.removeItem(ADMIN_TOKEN_KEY);
  };

  return {
    token,
    setToken,
    clearToken
  };
});
