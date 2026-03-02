/** Pinia-store пользовательской авторизации и профиля. */
import { defineStore } from "pinia";
import { ref } from "vue";

import { fetchMe, loginUser, logoutUser, registerUser } from "../api/user";
import {
  clearAuthTokens,
  getAccessToken,
  getRefreshToken,
  setAccessToken,
  setAuthTokens
} from "../api/jwtAuth";

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
  const token = ref<string | null>(getAccessToken());
  const refreshToken = ref<string | null>(getRefreshToken());
  const user = ref<AuthUser | null>(null);

  const setStoredTokens = (access: string | null, refresh: string | null) => {
    /** Синхронно обновляет state и localStorage для access/refresh токенов. */
    token.value = access;
    refreshToken.value = refresh;

    if (access && refresh) {
      setAuthTokens(access, refresh);
      return;
    }
    if (access) {
      clearAuthTokens();
      setAccessToken(access);
      return;
    }
    clearAuthTokens();
  };

  const readTokenPayload = (data: any) => {
    // Поддержка как новой JWT-формы, так и legacy `token`.
    const access =
      typeof data?.access === "string"
        ? data.access
        : typeof data?.token === "string"
          ? data.token
          : null;
    const refresh = typeof data?.refresh === "string" ? data.refresh : null;
    return { access, refresh };
  };

  const register = async (payload: { username: string; email?: string; password: string }) => {
    /** Регистрация + сохранение токенов + загрузка профиля. */
    const response = await registerUser(payload);
    const { access, refresh } = readTokenPayload(response.data);
    if (!access) {
      throw new Error("Access token is missing in register response");
    }
    setStoredTokens(access, refresh);
    await fetchMeProfile();
    return response.data;
  };

  const login = async (payload: { username_or_email: string; password: string }) => {
    /** Вход + сохранение токенов + загрузка профиля. */
    const response = await loginUser(payload);
    const { access, refresh } = readTokenPayload(response.data);
    if (!access) {
      throw new Error("Access token is missing in login response");
    }
    setStoredTokens(access, refresh);
    await fetchMeProfile();
    return response.data;
  };

  const fetchMeProfile = async () => {
    /** Загружает `/auth/me/` и валидирует текущую сессию на фронтенде. */
    if (!token.value) {
      user.value = null;
      return null;
    }
    try {
      const response = await fetchMe();
      user.value = response.data;
      return response.data;
    } catch {
      setStoredTokens(null, null);
      user.value = null;
      return null;
    }
  };

  const logout = async () => {
    /** Выход пользователя с очисткой токенов и локального профиля. */
    if (token.value) {
      try {
        await logoutUser();
      } catch {
        // ignore
      }
    }
    setStoredTokens(null, null);
    user.value = null;
  };

  return {
    token,
    refreshToken,
    user,
    register,
    login,
    fetchMe: fetchMeProfile,
    logout
  };
});
