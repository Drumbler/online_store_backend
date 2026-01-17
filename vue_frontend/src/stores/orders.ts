import { defineStore } from "pinia";
import { ref } from "vue";

import { checkout } from "../api/public";

export type CheckoutPayload = {
  name: string;
  phone: string;
  address: string;
};

export const useOrderStore = defineStore("orders", () => {
  const loading = ref(false);
  const error = ref<string | null>(null);
  const lastOrder = ref<any>(null);

  const submitCheckout = async (payload: CheckoutPayload) => {
    loading.value = true;
    error.value = null;
    try {
      const response = await checkout(payload);
      lastOrder.value = response.data;
      return response.data;
    } catch (err: any) {
      error.value = err?.response?.data?.detail || "Checkout failed.";
      return null;
    } finally {
      loading.value = false;
    }
  };

  return {
    loading,
    error,
    lastOrder,
    submitCheckout
  };
});
