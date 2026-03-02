/**
 * Публичный API-клиент витрины.
 * Содержит методы каталога, корзины, checkout, доставки, отзывов и оплаты.
 */
import axios from "axios";
import { installJwtInterceptors } from "./jwtAuth";

export const apiClient = axios.create({
  baseURL: "/api",
  withCredentials: true,
  headers: {
    "Content-Type": "application/json"
  }
});

installJwtInterceptors(apiClient);

export type ProductQueryParams = {
  page?: number;
  page_size?: number;
  category?: string;
  search?: string;
  ordering?: string;
};

/** Категории каталога (публичный endpoint). */
export const getCategories = () => apiClient.get("/categories/");

/** Список товаров с пагинацией/фильтрами/поиском/сортировкой. */
export const getProducts = (params: ProductQueryParams) =>
  apiClient.get("/products/", { params });

/** Детальная карточка товара по slug. */
export const getProductBySlug = (slug: string) =>
  apiClient.get(`/products/by-slug/${slug}/`);

/** Трекинг просмотра товара для аналитики. */
export const trackProductView = (productId: string) =>
  apiClient.post(`/products/${productId}/track-view/`);

/** Текущее состояние корзины (гостевой или пользовательской). */
export const getCart = () => apiClient.get("/cart/");

/** Добавление позиции в корзину. */
export const addCartItem = (payload: { product_id: string; quantity: number }) =>
  apiClient.post("/cart/items/", payload);

/** Обновление количества позиции корзины. */
export const updateCartItem = (pk: string | number, payload: { quantity: number }) =>
  apiClient.patch(`/cart/items/${pk}/`, payload);

/** Удаление позиции из корзины. */
export const deleteCartItem = (pk: string | number) =>
  apiClient.delete(`/cart/items/${pk}/`);

/** Legacy checkout endpoint. */
export const checkout = (payload: { name: string; phone: string; address: string }) =>
  apiClient.post("/orders/checkout/", payload);

/** Предварительный расчет checkout без фиксации заказа. */
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
}) => apiClient.post("/checkout/preview/", payload);

/** Финальное подтверждение checkout и создание заказа. */
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
}) => apiClient.post("/checkout/confirm/", payload);

/** Доступные методы доставки для текущего checkout-сценария. */
export const getCheckoutShippingMethods = () => apiClient.get("/checkout/shipping-methods/");

/** Поиск ПВЗ у выбранного провайдера доставки. */
export const getShippingPickupPoints = (providerId: string, city: string, q?: string) =>
  apiClient.get(`/shipping/${providerId}/pickup-points/`, { params: { city, q } });

/** Расчет стоимости доставки у выбранного провайдера. */
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
) => apiClient.post(`/shipping/${providerId}/quote/`, payload);

/** Публичный поиск заказа по номеру и секрету. */
export const lookupOrder = (number: string, order_secret: string) =>
  apiClient.get("/orders/lookup/", { params: { number, order_secret } });

/** Список отзывов конкретного товара с фильтрами. */
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

/** Сводка рейтингов для набора товаров (для каталога/карточек). */
export const getReviewsSummary = (productIds: string[]) =>
  apiClient.get<{ results: Record<string, ReviewRatingSummary> }>("/reviews/summary/", {
    params: {
      product_ids: productIds.join(",")
    }
  });

/** Товары, для которых пользователь может оставить отзыв. */
export const getEligibleReviewProducts = (params?: {
  order_number?: string;
  order_secret?: string;
}) => apiClient.get("/reviews/eligible/", { params });

/** Создание отзыва по review_token. */
export const submitReview = (payload: {
  review_token: string;
  rating: number;
  pros?: string;
  cons?: string;
  comment?: string;
  is_anonymous: boolean;
}) => apiClient.post("/reviews/", payload);

/** Список доступных платежных провайдеров для checkout. */
export const getCheckoutPaymentMethods = () => apiClient.get("/checkout/payment-methods/");

/** Создает платеж через выбранного провайдера. */
export const createPayment = (payload: {
  order_number: string;
  order_secret?: string;
  provider_id: string;
}) => apiClient.post("/payments/", payload);

/** Тестовый webhook для эмуляции колбэка платежного провайдера. */
export const postPaymentWebhook = (
  providerId: string,
  payload: { external_id: string; status: "succeeded" | "failed" }
) => apiClient.post(`/payments/webhook/${providerId}/`, payload);
