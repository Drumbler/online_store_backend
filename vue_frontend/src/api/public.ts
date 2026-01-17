import axios from "axios";

export const apiClient = axios.create({
  baseURL: "/api",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json"
  }
});

export type ProductQueryParams = {
  page?: number;
  page_size?: number;
  category?: string;
  search?: string;
  ordering?: string;
};

export const getCategories = () => apiClient.get("/categories/");

export const getProducts = (params: ProductQueryParams) =>
  apiClient.get("/products/", { params });

export const getProductBySlug = (slug: string) =>
  apiClient.get(`/products/by-slug/${slug}/`);

export const getCart = () => apiClient.get("/cart/");

export const addCartItem = (payload: { product_id: string; quantity: number }) =>
  apiClient.post("/cart/items/", payload);

export const updateCartItem = (pk: string | number, payload: { quantity: number }) =>
  apiClient.patch(`/cart/items/${pk}/`, payload);

export const deleteCartItem = (pk: string | number) =>
  apiClient.delete(`/cart/items/${pk}/`);

export const checkout = (payload: { name: string; phone: string; address: string }) => {
  const token = localStorage.getItem("authToken");
  const headers = token ? { Authorization: `Token ${token}` } : undefined;
  return apiClient.post("/orders/checkout/", payload, { headers });
};

export const lookupOrder = (number: string) =>
  apiClient.get("/orders/lookup/", { params: { number } });
