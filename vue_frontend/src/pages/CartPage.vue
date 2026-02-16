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
          <td>{{ item.product.title || item.product.id }}</td>
          <td>
            <div class="price">
              <template v-if="item.discount_percent > 0">
                <span class="old">
                  {{ item.unit_price_original }} {{ item.product.currency || "RUB" }}
                </span>
                <span class="new">
                  {{ item.unit_price_final }} {{ item.product.currency || "RUB" }}
                </span>
                <span class="badge">-{{ item.discount_percent }}%</span>
              </template>
              <template v-else>
                <span>{{ item.unit_price_final }} {{ item.product.currency || "RUB" }}</span>
              </template>
            </div>
          </td>
          <td>
            <input
              type="number"
              min="1"
              :value="item.quantity"
              @change="onQtyChange(item, $event)"
            />
          </td>
          <td>{{ item.line_total }} {{ item.product.currency || "RUB" }}</td>
          <td>
            <button @click="cartStore.removeItem(item.id)">Remove</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="cartStore.cart" class="summary">
      <div>Subtotal: {{ cartStore.cart.subtotal_original }} RUB</div>
      <div>Discount: -{{ cartStore.cart.discount_total }} RUB</div>
      <div class="total">Total: {{ cartStore.cart.total }} RUB</div>
    </div>

    <div class="actions">
      <RouterLink to="/checkout">Checkout</RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
import { onMounted } from "vue";
import { useCartStore, type CartItem } from "../stores/cart";

const cartStore = useCartStore();

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

.price {
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.old {
  text-decoration: line-through;
  color: #8a7b68;
}

.new {
  font-weight: 600;
  color: #2f4b2f;
}

.badge {
  display: inline-flex;
  width: fit-content;
  padding: 2px 8px;
  border-radius: 999px;
  background: #efe4cf;
  color: #4b3c2f;
  font-size: 12px;
}

.summary {
  align-self: flex-end;
  min-width: 260px;
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
