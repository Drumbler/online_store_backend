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

export const trackProductView = (productId: string) =>
  apiClient.post(`/products/${productId}/track-view/`);

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

export const previewCheckout = (payload: {
  address: {
    city: string;
    postal_code: string;
    street: string;
    house: string;
  };
  shipping_provider: string;
  shipping_type: "pickup" | "courier";
  pickup_point_id?: string;
  comment?: string;
}) => apiClient.post("/checkout/preview/", payload, { headers: authHeaders() });

export const confirmCheckout = (payload: {
  address: {
    city: string;
    postal_code: string;
    street: string;
    house: string;
  };
  shipping_provider: string;
  shipping_type: "pickup" | "courier";
  pickup_point_id?: string;
  comment?: string;
}) => apiClient.post("/checkout/confirm/", payload, { headers: authHeaders() });

export const getCheckoutShippingMethods = () => apiClient.get("/checkout/shipping-methods/");

export const getShippingPickupPoints = (providerId: string, city: string, q?: string) =>
  apiClient.get(`/shipping/${providerId}/pickup-points/`, { params: { city, q } });

export const getShippingQuote = (
  providerId: string,
  payload: {
    address: {
      city: string;
      postal_code: string;
      street: string;
      house: string;
    };
    shipping_type: "pickup" | "courier";
    pickup_point_id?: string;
    comment?: string;
  }
) => apiClient.post(`/shipping/${providerId}/quote/`, payload, { headers: authHeaders() });

const authHeaders = () => {
  const token = localStorage.getItem("authToken");
  return token ? { Authorization: `Token ${token}` } : undefined;
};

export const lookupOrder = (number: string, order_secret: string) =>
  apiClient.get("/orders/lookup/", { params: { number, order_secret } });

export const getProductReviews = (
  productId: string,
  params?: {
    limit?: number;
    page?: number;
    page_size?: number;
    rating_gte?: number;
    sort?: "created_desc" | "created_asc" | "rating_desc" | "rating_asc";
  }
) => apiClient.get(`/products/${productId}/reviews/`, { params });

export type ReviewRatingSummary = {
  avg_rating: number | null;
  reviews_count: number;
};

export const getReviewsSummary = (productIds: string[]) =>
  apiClient.get<{ results: Record<string, ReviewRatingSummary> }>("/reviews/summary/", {
    params: {
      product_ids: productIds.join(",")
    }
  });

export const getEligibleReviewProducts = (params?: {
  order_number?: string;
  order_secret?: string;
}) => apiClient.get("/reviews/eligible/", { params, headers: authHeaders() });

export const submitReview = (payload: {
  review_token: string;
  rating: number;
  pros?: string;
  cons?: string;
  comment?: string;
  is_anonymous: boolean;
}) => apiClient.post("/reviews/", payload, { headers: authHeaders() });

export const getCheckoutPaymentMethods = () => apiClient.get("/checkout/payment-methods/");

export const createPayment = (payload: {
  order_number: string;
  order_secret?: string;
  provider_id: string;
}) => apiClient.post("/payments/", payload, { headers: authHeaders() });

export const postPaymentWebhook = (providerId: string, payload: { external_id: string; status: "succeeded" | "failed" }) =>
  apiClient.post(`/payments/webhook/${providerId}/`, payload, { headers: authHeaders() });
