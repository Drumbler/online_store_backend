<template>
  <section class="page bg-app text-app">
    <h1>Корзина</h1>

    <div v-if="cartStore.loading" class="state-box">Загрузка...</div>
    <div v-else-if="cartStore.error" class="state-box error">{{ cartStore.error }}</div>

    <table v-else class="table surface-card">
      <thead>
        <tr>
          <th>Товар</th>
          <th>Цена</th>
          <th>Кол-во</th>
          <th>Сумма</th>
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
            <button class="btn btn-neutral btn-remove" @click="cartStore.removeItem(item.id)">Удалить</button>
          </td>
        </tr>
      </tbody>
    </table>

    <div v-if="cartStore.cart" class="summary surface-card">
      <div>Подытог: {{ cartStore.cart.subtotal_original }} RUB</div>
      <div>Скидка: -{{ cartStore.cart.discount_total }} RUB</div>
      <div class="total">Итого: {{ cartStore.cart.total }} RUB</div>
    </div>

    <div class="actions">
      <RouterLink to="/checkout" class="btn btn-primary">Оформить заказ</RouterLink>
    </div>
  </section>
</template>

<script setup lang="ts">
/** Логика страницы и обработчики UI состояния. */
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
  border-spacing: 0;
  overflow: hidden;
}

th, td {
  border-bottom: 1px solid var(--border);
  padding: 8px;
  text-align: left;
}

th {
  color: var(--muted);
  font-weight: 600;
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
  color: var(--muted);
}

.new {
  font-weight: 600;
  color: var(--primary);
}

.badge {
  display: inline-flex;
  width: fit-content;
  padding: 2px 8px;
  border-radius: 999px;
  background: var(--primary-soft);
  color: var(--primary-soft-contrast);
  font-size: 12px;
}

.summary {
  align-self: flex-end;
  min-width: 260px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
}

.summary .total {
  font-weight: 700;
}

.btn-remove {
  min-height: 34px;
  padding: 6px 10px;
}
</style>
