<template>
  <section class="page">
    <h1>Cart</h1>

    <div v-if="cartStore.loading" class="status">Loading...</div>
    <div v-else-if="cartStore.error" class="status error">{{ cartStore.error }}</div>

    <table v-else class="table">
      <thead>
        <tr>
          <th>Item</th>
          <th>Price</th>
          <th>Qty</th>
          <th>Subtotal</th>
          <th></th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="item in cartStore.items" :key="item.id">
          <td>{{ item.product_title_snapshot || item.product_id }}</td>
          <td>{{ item.unit_price_snapshot }}</td>
          <td>
            <input
              type="number"
              min="1"
              :value="item.quantity"
              @change="onQtyChange(item, $event)"
            />
          </td>
          <td>{{ lineTotal(item) }}</td>
          <td>
            <button @click="cartStore.removeItem(item.id)">Remove</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div class="actions">
      <RouterLink to="/checkout">Checkout</RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useCartStore, type CartItem } from "../stores/cart";

const cartStore = useCartStore();

const lineTotal = (item: CartItem) => {
  const price = Number(item.unit_price_snapshot || 0);
  return (price * Number(item.quantity || 0)).toFixed(2);
};

const onQtyChange = (item: CartItem, event: Event) => {
  const target = event.target as HTMLInputElement;
  const qty = Number(target.value || 1);
  if (qty > 0) {
    cartStore.setQty(item.id, qty);
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

.table {
  width: 100%;
  border-collapse: collapse;
}

th, td {
  border-bottom: 1px solid #e0e0e0;
  padding: 8px;
  text-align: left;
}

.actions {
  display: flex;
  justify-content: flex-end;
}

.status {
  padding: 12px;
  background: #fff6d8;
  border: 1px solid #f0dca0;
}

.status.error {
  background: #ffe1e1;
  border-color: #f2b3b3;
}
</style>
