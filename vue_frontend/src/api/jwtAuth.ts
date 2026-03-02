/**
 * Общая JWT-обвязка для axios-клиентов:
 * - хранение access/refresh в localStorage;
 * - автоматическая подстановка Bearer токена;
 * - одноразовый refresh при 401 и повтор запроса.
 */
import axios from "axios";
import type { AxiosError, AxiosInstance, InternalAxiosRequestConfig } from "axios";

const ACCESS_TOKEN_KEY = "authToken";
const REFRESH_TOKEN_KEY = "authRefreshToken";
const LEGACY_ADMIN_TOKEN_KEY = "adminToken";

type RetriableConfig = InternalAxiosRequestConfig & { _retry?: boolean };

const configuredClients = new WeakSet<AxiosInstance>();

let refreshRequest: Promise<string | null> | null = null;
let redirectScheduled = false;

const getStorage = () => {
  if (typeof window === "undefined") {
    return null;
  }
  return window.localStorage;
};

const isAuthBypassUrl = (url?: string) => {
  // Для auth-эндпоинтов не добавляем Bearer и не запускаем refresh-цикл.
  const normalized = String(url || "");
  return (
    normalized.includes("/auth/jwt/create/") ||
    normalized.includes("/auth/jwt/refresh/") ||
    normalized.includes("/auth/jwt/verify/") ||
    normalized.includes("/auth/login/") ||
    normalized.includes("/auth/register/")
  );
};

const removeLegacyAdminToken = () => {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  storage.removeItem(LEGACY_ADMIN_TOKEN_KEY);
};

export const getAccessToken = () => getStorage()?.getItem(ACCESS_TOKEN_KEY) || null;

export const getRefreshToken = () => getStorage()?.getItem(REFRESH_TOKEN_KEY) || null;

export const setAuthTokens = (access: string, refresh: string) => {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  storage.setItem(ACCESS_TOKEN_KEY, access);
  storage.setItem(REFRESH_TOKEN_KEY, refresh);
  removeLegacyAdminToken();
};

export const setAccessToken = (access: string) => {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  storage.setItem(ACCESS_TOKEN_KEY, access);
  removeLegacyAdminToken();
};

export const clearAuthTokens = () => {
  const storage = getStorage();
  if (!storage) {
    return;
  }
  storage.removeItem(ACCESS_TOKEN_KEY);
  storage.removeItem(REFRESH_TOKEN_KEY);
  removeLegacyAdminToken();
};

const redirectToLogin = () => {
  // Избегаем множественных редиректов при пачке параллельных 401.
  if (typeof window === "undefined" || redirectScheduled) {
    return;
  }
  if (window.location.pathname === "/login") {
    return;
  }
  redirectScheduled = true;
  const currentPath = `${window.location.pathname}${window.location.search}`;
  const redirectTarget = encodeURIComponent(currentPath || "/");
  window.location.assign(`/login?redirect=${redirectTarget}`);
};

const requestAccessRefresh = async (): Promise<string | null> => {
  /** Запрашивает новый access по refresh и обновляет storage. */
  const refresh = getRefreshToken();
  if (!refresh) {
    clearAuthTokens();
    return null;
  }
  try {
    const response = await axios.post(
      "/api/auth/jwt/refresh/",
      { refresh },
      {
        headers: {
          "Content-Type": "application/json"
        }
      }
    );

    const access = response.data?.access;
    if (typeof access !== "string" || !access) {
      throw new Error("Missing access token");
    }

    if (typeof response.data?.refresh === "string" && response.data.refresh) {
      setAuthTokens(access, response.data.refresh);
      return access;
    }

    setAccessToken(access);
    return access;
  } catch {
    clearAuthTokens();
    return null;
  }
};

const refreshAccessToken = async () => {
  // Все конкурирующие 401 делят один refresh-запрос.
  if (!refreshRequest) {
    refreshRequest = requestAccessRefresh().finally(() => {
      refreshRequest = null;
    });
  }
  return refreshRequest;
};

export const installJwtInterceptors = (client: AxiosInstance) => {
  /** Подключает request/response interceptors к переданному axios-клиенту. */
  if (configuredClients.has(client)) {
    return;
  }
  configuredClients.add(client);

  client.interceptors.request.use((config) => {
    if (isAuthBypassUrl(config.url)) {
      return config;
    }
    const access = getAccessToken();
    if (access) {
      config.headers = config.headers || {};
      config.headers.Authorization = `Bearer ${access}`;
    }
    return config;
  });

  client.interceptors.response.use(
    (response) => response,
    async (error: AxiosError) => {
      const status = error.response?.status;
      const originalConfig = error.config as RetriableConfig | undefined;
      if (status !== 401 || !originalConfig) {
        return Promise.reject(error);
      }
      if (originalConfig._retry || isAuthBypassUrl(originalConfig.url)) {
        return Promise.reject(error);
      }

      const hasAuthContext = Boolean(
        getAccessToken() || getRefreshToken() || originalConfig.headers?.Authorization
      );
      const refresh = getRefreshToken();
      if (!refresh) {
        if (hasAuthContext) {
          clearAuthTokens();
          redirectToLogin();
        }
        return Promise.reject(error);
      }

      originalConfig._retry = true;
      const nextAccess = await refreshAccessToken();
      if (!nextAccess) {
        if (hasAuthContext) {
          redirectToLogin();
        }
        return Promise.reject(error);
      }

      originalConfig.headers = originalConfig.headers || {};
      originalConfig.headers.Authorization = `Bearer ${nextAccess}`;
      return client(originalConfig);
    }
  );
};
