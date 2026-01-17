import { createRouter, createWebHistory } from "vue-router";

import CatalogPage from "../pages/CatalogPage.vue";
import CategoriesPage from "../pages/CategoriesPage.vue";
import ProductPage from "../pages/ProductPage.vue";
import CartPage from "../pages/CartPage.vue";
import CheckoutPage from "../pages/CheckoutPage.vue";
import OrdersPage from "../pages/OrdersPage.vue";
import LoginPage from "../pages/LoginPage.vue";
import RegisterPage from "../pages/RegisterPage.vue";
import AdminLayout from "../layouts/AdminLayout.vue";
import AdminLoginPage from "../pages/AdminLoginPage.vue";
import AdminProductsPage from "../pages/AdminProductsPage.vue";
import AdminCategoriesPage from "../pages/AdminCategoriesPage.vue";
import AdminOrdersPage from "../pages/AdminOrdersPage.vue";
import AdminReportsPage from "../pages/AdminReportsPage.vue";

const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: "/", name: "catalog", component: CatalogPage },
    { path: "/categories", name: "categories", component: CategoriesPage },
    { path: "/p/:slug", name: "product", component: ProductPage, props: true },
    { path: "/cart", name: "cart", component: CartPage },
    { path: "/checkout", name: "checkout", component: CheckoutPage },
    { path: "/orders", name: "orders", component: OrdersPage },
    { path: "/login", name: "login", component: LoginPage },
    { path: "/register", name: "register", component: RegisterPage },
    { path: "/admin/login", name: "admin-login", component: AdminLoginPage },
    {
      path: "/admin",
      component: AdminLayout,
      children: [
        { path: "", redirect: "/admin/products" },
        { path: "products", name: "admin-products", component: AdminProductsPage },
        { path: "categories", name: "admin-categories", component: AdminCategoriesPage },
        { path: "orders", name: "admin-orders", component: AdminOrdersPage },
        { path: "reports", name: "admin-reports", component: AdminReportsPage }
      ]
    }
  ]
});

router.beforeEach((to) => {
  if (to.path.startsWith("/admin") && to.path !== "/admin/login") {
    const token = localStorage.getItem("adminToken");
    if (!token) {
      return { path: "/admin/login", query: { redirect: to.fullPath } };
    }
  }
  return true;
});

export default router;
