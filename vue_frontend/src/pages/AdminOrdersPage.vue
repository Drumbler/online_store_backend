<template>
  <section class="page bg-app text-app">
    <header class="heading">
      <h1>Заказы</h1>
      <p>Раздел управления заказами в разработке.</p>
    </header>
    <div class="placeholder surface-card">Здесь будет панель управления заказами.</div>
  </section>
</template>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.heading p {
  color: var(--muted);
}

.placeholder {
  padding: 16px;
}
</style>
