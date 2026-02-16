<template>
  <section class="page">
    <h1>Checkout</h1>

    <form class="form" @submit.prevent="submit">
      <label>
        Name
        <input v-model="name" required />
      </label>
      <label>
        Phone
        <input v-model="phone" required />
      </label>
      <label>
        Address
        <textarea v-model="address" rows="3" required></textarea>
      </label>
      <button type="submit" :disabled="orderStore.loading">Place order</button>
    </form>

    <div v-if="cartStore.cart" class="summary">
      <div>Subtotal: {{ cartStore.cart.subtotal_original }} RUB</div>
      <div>Discount: -{{ cartStore.cart.discount_total }} RUB</div>
      <div class="total">Total: {{ cartStore.cart.total }} RUB</div>
    </div>

    <div v-if="orderStore.error" class="status error">{{ orderStore.error }}</div>
    <div v-if="success" class="status">
      Order created. Number #{{ orderStore.lastOrder?.order_number ?? orderStore.lastOrder?.id }}.
      <RouterLink to="/orders">{{ ordersLinkLabel }}</RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from "vue";
import { useOrderStore } from "../stores/orders";
import { useAuthStore } from "../stores/auth";
import { useCartStore } from "../stores/cart";

const orderStore = useOrderStore();
const authStore = useAuthStore();
const cartStore = useCartStore();

const name = ref("");
const phone = ref("");
const address = ref("");
const success = ref(false);

const ordersLinkLabel = computed(() => (authStore.token ? "View my orders" : "Track order"));

const submit = async () => {
  success.value = false;
  const payload = {
    name: name.value,
    phone: phone.value,
    address: address.value
  };
  const result = await orderStore.submitCheckout(payload);
  if (result) {
    success.value = true;
    await cartStore.fetchCart();
  }
};

onMounted(() => {
  cartStore.fetchCart();
});
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.form {
  display: flex;
  flex-direction: column;
  gap: 12px;
  max-width: 420px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.status {
  padding: 12px;
  background: #e7f7e7;
  border: 1px solid #bfe3bf;
}

.status.error {
  background: #ffe1e1;
  border-color: #f2b3b3;
}

.summary {
  max-width: 420px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
  border: 1px solid #e0e0e0;
  background: #fff;
}

.summary .total {
  font-weight: 700;
}
</style>
