import axios from "axios";

export const userApiClient = axios.create({
  baseURL: "/api",
  headers: {
    "Content-Type": "application/json"
  }
});

userApiClient.interceptors.request.use((config) => {
  const token = localStorage.getItem("authToken");
  if (token) {
    config.headers = config.headers || {};
    config.headers.Authorization = `Token ${token}`;
  }
  return config;
});

export type RegisterPayload = {
  username: string;
  email?: string;
  password: string;
};

export type LoginPayload = {
  username_or_email: string;
  password: string;
};

export const registerUser = (payload: RegisterPayload) =>
  userApiClient.post("/auth/register/", payload);

export const loginUser = (payload: LoginPayload) =>
  userApiClient.post("/auth/login/", payload);

export const fetchMe = () => userApiClient.get("/auth/me/");

export const logoutUser = () => userApiClient.post("/auth/logout/");

export const getUserOrders = () => userApiClient.get("/orders/");

export type AccountProfile = {
  id: number;
  username: string;
  name: string | null;
  email: string | null;
  email_verified: boolean;
};

export const fetchAccountProfile = () => userApiClient.get("/account/me/");

export const updateAccountName = (payload: { name: string | null }) =>
  userApiClient.patch("/account/me/", payload);

export const setAccountEmail = (payload: { email: string }) =>
  userApiClient.post("/account/email/set/", payload);

export const requestEmailVerification = () =>
  userApiClient.post("/account/email/request-verification/");

export const verifyEmailToken = (payload: { token: string }) =>
  userApiClient.post("/account/email/verify/", payload);

export const changePassword = (payload: {
  current_password: string;
  new_password: string;
  new_password_confirm: string;
}) => userApiClient.post("/account/change-password/", payload);
