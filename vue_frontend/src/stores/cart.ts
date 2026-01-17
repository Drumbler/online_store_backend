import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { addCartItem, deleteCartItem, getCart, updateCartItem } from "../api/public";

export type CartItem = {
  id: number | string;
  product_id: string;
  product_title_snapshot?: string;
  unit_price_snapshot?: string;
  quantity: number;
};

export type Cart = {
  id: number | string;
  items: CartItem[];
  total_quantity?: number;
  total_price?: string;
};

const normalizeCartItems = (raw: any): CartItem[] => {
  if (!raw || !Array.isArray(raw.items)) {
    return [];
  }
  return raw.items as CartItem[];
};

export const useCartStore = defineStore("cart", () => {
  const cart = ref<Cart | null>(null);
  const items = ref<CartItem[]>([]);
  const loading = ref(false);
  const error = ref<string | null>(null);

  const cartCount = computed(() =>
    items.value.reduce((sum, item) => sum + Number(item.quantity || 0), 0)
  );

  const fetchCart = async () => {
    loading.value = true;
    error.value = null;
    try {
      const response = await getCart();
      cart.value = response.data as Cart;
      items.value = normalizeCartItems(cart.value);
    } catch (err: any) {
      error.value = err?.response?.data?.detail || "Failed to load cart.";
    } finally {
      loading.value = false;
    }
  };

  const addToCart = async (productId: string, qty = 1) => {
    loading.value = true;
    error.value = null;
    try {
      await addCartItem({ product_id: productId, quantity: qty });
      await fetchCart();
    } catch (err: any) {
      error.value = err?.response?.data?.detail || "Failed to add item.";
      loading.value = false;
    }
  };

  const setQty = async (itemPk: string | number, qty: number) => {
    loading.value = true;
    error.value = null;
    try {
      await updateCartItem(itemPk, { quantity: qty });
      await fetchCart();
    } catch (err: any) {
      error.value = err?.response?.data?.detail || "Failed to update quantity.";
      loading.value = false;
    }
  };

  const removeItem = async (itemPk: string | number) => {
    loading.value = true;
    error.value = null;
    try {
      await deleteCartItem(itemPk);
      await fetchCart();
    } catch (err: any) {
      error.value = err?.response?.data?.detail || "Failed to remove item.";
      loading.value = false;
    }
  };

  return {
    cart,
    items,
    loading,
    error,
    cartCount,
    fetchCart,
    addToCart,
    setQty,
    removeItem
  };
});
