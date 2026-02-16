import { defineStore } from "pinia";
import { ref } from "vue";
import type { RouteLocationNormalizedLoaded } from "vue-router";

import { getCategories, getProductBySlug, getProducts } from "../api/public";

export type Category = {
  id: string;
  title?: string;
  slug?: string;
};

export type Product = {
  id: string;
  slug?: string;
  title?: string;
  description?: string | null;
  price?: string;
  discounted_price?: string | null;
  discount_percent?: number;
  currency?: string;
  image_url?: string | null;
  thumbnail_url?: string | null;
  category?: Category | null;
};

type ProductsResponse = {
  results: Product[];
  pagination: {
    page: number;
    page_size: number;
    total: number;
  };
};

export const useCatalogStore = defineStore("catalog", () => {
  const categories = ref<Category[]>([]);
  const products = ref<Product[]>([]);
  const pagination = ref({ page: 1, page_size: 20, total: 0 });
  const loading = ref(false);
  const error = ref<string | null>(null);

  const fetchCategories = async () => {
    loading.value = true;
    error.value = null;
    try {
      const response = await getCategories();
      categories.value = response.data.results || [];
    } catch (err: any) {
      error.value = err?.response?.data?.detail || "Failed to load categories.";
    } finally {
      loading.value = false;
    }
  };

  const fetchProductsFromRouteQuery = async (query: RouteLocationNormalizedLoaded["query"]) => {
    loading.value = true;
    error.value = null;
    try {
      const params: Record<string, string | number> = {};
      if (typeof query.category === "string") {
        params.category = query.category;
      }
      if (typeof query.search === "string") {
        params.search = query.search;
      }
      if (typeof query.ordering === "string") {
        params.ordering = query.ordering;
      }
      if (typeof query.page === "string") {
        const parsed = Number(query.page);
        if (!Number.isNaN(parsed)) {
          params.page = parsed;
        }
      }
      if (typeof query.page_size === "string") {
        const parsed = Number(query.page_size);
        if (!Number.isNaN(parsed)) {
          params.page_size = parsed;
        }
      }
      const response = await getProducts(params);
      const payload = response.data as ProductsResponse;
      products.value = payload.results || [];
      pagination.value = payload.pagination || { page: 1, page_size: 20, total: 0 };
    } catch (err: any) {
      error.value = err?.response?.data?.detail || "Failed to load products.";
    } finally {
      loading.value = false;
    }
  };

  const fetchProductBySlug = async (slug: string) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await getProductBySlug(slug);
      return response.data as Product;
    } catch (err: any) {
      error.value = err?.response?.data?.detail || "Failed to load product.";
      return null;
    } finally {
      loading.value = false;
    }
  };

  return {
    categories,
    products,
    pagination,
    loading,
    error,
    fetchCategories,
    fetchProductsFromRouteQuery,
    fetchProductBySlug
  };
});
