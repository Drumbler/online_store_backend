<template>
  <section class="page">
    <div v-if="catalogStore.loading" class="status">Loading...</div>
    <div v-else-if="catalogStore.error" class="status error">{{ catalogStore.error }}</div>

    <div v-else-if="product" class="product">
      <img
        v-if="product.image_url"
        :src="product.image_url"
        :alt="product.title"
        class="image"
      />
      <div v-else class="placeholder">No image</div>
      
      <div class="details">
        <h1>{{ product.title }}</h1>
        <div class="price">
          <template v-if="hasDiscount(product)">
            <span class="old">{{ product.price }} {{ product.currency }}</span>
            <span class="new">{{ discountedPrice(product) }} {{ product.currency }}</span>
            <span class="badge">-{{ product.discount_percent }}%</span>
          </template>
          <template v-else>
            <span>{{ product.price }} {{ product.currency }}</span>
          </template>
        </div>
        <p class="description">{{ product.description || "No description" }}</p>

        <label class="qty">
          Qty
          <select v-model.number="qty">
            <option v-for="n in 10" :key="n" :value="n">{{ n }}</option>
          </select>
        </label>

        <button @click="addToCart">Add to cart</button>
      </div>
    </div>
  </section>
  
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { useRoute } from "vue-router";
import { useCartStore } from "../stores/cart";
import { useCatalogStore, type Product } from "../stores/catalog";

const route = useRoute();
const catalogStore = useCatalogStore();
const cartStore = useCartStore();

const product = ref<Product | null>(null);
const qty = ref(1);

const addToCart = () => {
  if (!product.value?.id) {
    return;
  }
  cartStore.addToCart(product.value.id, qty.value);
};

const hasDiscount = (item: Product) => {
  const discount = Number(item.discount_percent || 0);
  return discount > 0;
};

const discountedPrice = (item: Product) => {
  if (item.discounted_price) {
    return item.discounted_price;
  }
  const price = Number(item.price || 0);
  const discount = Number(item.discount_percent || 0);
  return (price * (1 - discount / 100)).toFixed(2);
};

onMounted(async () => {
  product.value = await catalogStore.fetchProductBySlug(String(route.params.slug || ""));
});

</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
}

.product {
  display: grid;
  grid-template-columns: 320px 1fr;
  gap: 24px;
  align-items: start;
}

.image {
  width: 100%;
  border: 1px solid #eee;
}

.placeholder {
  width: 100%;
  height: 240px;
  background: #f0f0f0;
  display: flex;
  align-items: center;
  justify-content: center;
  color: #666;
}

.details {
  display: flex;
  flex-direction: column;
  gap: 12px;
}

.price {
  display: flex;
  flex-direction: column;
  gap: 4px;
  font-weight: 600;
}

.price .old {
  text-decoration: line-through;
  color: #8a7b68;
  font-weight: 400;
}

.price .new {
  color: #2f4b2f;
}

.badge {
  display: inline-flex;
  align-items: center;
  padding: 2px 8px;
  border-radius: 999px;
  background: #efe4cf;
  color: #4b3c2f;
  font-size: 12px;
  width: fit-content;
}

.qty {
  display: flex;
  flex-direction: column;
  gap: 4px;
  width: 80px;
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

@media (max-width: 900px) {
  .product {
    grid-template-columns: 1fr;
  }
}
</style>

