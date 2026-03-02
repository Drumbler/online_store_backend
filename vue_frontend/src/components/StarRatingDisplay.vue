<template>
  <span class="stars" :style="{ fontSize: size }" :aria-label="label">
    <span class="stars-base">★★★★★</span>
    <span class="stars-fill" :style="{ width: `${fillPercent}%` }">★★★★★</span>
  </span>
</template>

<script setup lang="ts">
/** Логика страницы и обработчики UI состояния. */
import { computed } from "vue";

const props = withDefaults(
  defineProps<{
    rating: number | null;
    size?: string;
  }>(),
  {
    size: "14px"
  }
);

const safeRating = computed(() => {
  const value = Number(props.rating ?? 0);
  if (Number.isNaN(value)) {
    return 0;
  }
  return Math.max(0, Math.min(5, value));
});

const fillPercent = computed(() => (safeRating.value / 5) * 100);
const label = computed(() => `${safeRating.value.toFixed(1)} out of 5 stars`);
</script>

<style scoped>
.stars {
  position: relative;
  display: inline-block;
  line-height: 1;
  letter-spacing: 0.08em;
}

.stars-base {
  color: #d8d8d8;
}

.stars-fill {
  position: absolute;
  inset: 0 auto 0 0;
  overflow: hidden;
  white-space: nowrap;
  color: #d79a2c;
}
</style>
