/** Pinia-store корзины: загрузка, изменение количества и удаление позиций. */
import { defineStore } from "pinia";
import { computed, ref } from "vue";

import { addCartItem, deleteCartItem, getCart, updateCartItem } from "../api/public";

export type CartItem = {
  id: number | string;
  product: {
    id: string;
    title?: string;
    slug?: string;
    image_url?: string | null;
    thumbnail_url?: string | null;
    currency?: string;
  };
  unit_price_original: string;
  discount_percent: number;
  unit_price_final: string;
  line_total: string;
  quantity: number;
};

export type Cart = {
  id: number | string;
  items: CartItem[];
  total_quantity: number;
  subtotal_original: string;
  subtotal_final: string;
  discount_total: string;
  total: string;
  total_price?: string;
};

const normalizeCartItems = (raw: any): CartItem[] => {
  /** Приводит неизвестный payload корзины к массиву позиций. */
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
    // Количество единиц товара, а не количество строк корзины.
    items.value.reduce((sum, item) => sum + Number(item.quantity || 0), 0)
  );

  const fetchCart = async () => {
    /** Загружает текущее состояние корзины. */
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
    /** Добавляет товар в корзину и перечитывает ее состояние. */
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
    /** Обновляет количество позиции и перечитывает корзину. */
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
    /** Удаляет позицию корзины и перечитывает состояние. */
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
