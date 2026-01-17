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
