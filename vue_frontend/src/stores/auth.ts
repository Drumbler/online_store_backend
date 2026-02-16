import { defineStore } from "pinia";
import { ref } from "vue";

import { fetchMe, loginUser, logoutUser, registerUser } from "../api/user";

export type AuthUser = {
  id: number | string;
  username: string;
  email?: string;
  name?: string;
  is_staff?: boolean;
  is_superuser?: boolean;
  is_admin?: boolean;
};

export const useAuthStore = defineStore("auth", () => {
  const token = ref<string | null>(localStorage.getItem("authToken"));
  const user = ref<AuthUser | null>(null);

  const setToken = (value: string | null) => {
    token.value = value;
    if (value) {
      localStorage.setItem("authToken", value);
    } else {
      localStorage.removeItem("authToken");
    }
  };

  const register = async (payload: { username: string; email?: string; password: string }) => {
    const response = await registerUser(payload);
    setToken(response.data.token);
    await fetchMeProfile();
    return response.data;
  };

  const login = async (payload: { username_or_email: string; password: string }) => {
    const response = await loginUser(payload);
    setToken(response.data.token);
    await fetchMeProfile();
    return response.data;
  };

  const fetchMeProfile = async () => {
    if (!token.value) {
      user.value = null;
      return null;
    }
    try {
      const response = await fetchMe();
      user.value = response.data;
      return response.data;
    } catch {
      setToken(null);
      user.value = null;
      return null;
    }
  };

  const logout = async () => {
    if (token.value) {
      try {
        await logoutUser();
      } catch {
        // ignore
      }
    }
    setToken(null);
    user.value = null;
  };

  return {
    token,
    user,
    register,
    login,
    fetchMe: fetchMeProfile,
    logout
  };
});
