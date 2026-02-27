<template>
  <section class="page bg-app text-app">
    <h1>Checkout</h1>

    <form class="form surface-card" @submit.prevent>
      <label>
        City
        <input v-model="address.city" required />
      </label>
      <label>
        Postal code
        <input v-model="address.postal_code" :required="shippingType === 'courier'" />
      </label>
      <label>
        Street
        <input v-model="address.street" required />
      </label>
      <label>
        House
        <input v-model="address.house" required />
      </label>

      <label>
        Shipping provider
        <select v-model="shippingProvider" :disabled="loadingMethods || submittingConfirm || calculating">
          <option v-for="method in shippingMethods" :key="method.provider_id" :value="method.provider_id">
            {{ method.title }}
          </option>
        </select>
      </label>

      <div class="mode-field">
        <span class="mode-label">Delivery mode</span>
        <div class="mode-switch" role="radiogroup" aria-label="Delivery mode">
          <button
            type="button"
            class="mode-button"
            :class="{ active: shippingType === 'courier' }"
            :disabled="submittingConfirm || calculating"
            @click="shippingType = 'courier'"
          >
            Courier
          </button>
          <button
            type="button"
            class="mode-button"
            :class="{ active: shippingType === 'pickup' }"
            :disabled="submittingConfirm || calculating"
            @click="shippingType = 'pickup'"
          >
            Pickup
          </button>
        </div>
      </div>

      <div v-if="shippingType === 'pickup'" class="pickup-block">
        <label>
          Pickup point
          <select v-model="pickupPointId" :disabled="loadingPickupPoints || submittingConfirm || calculating">
            <option value="">Select pickup point</option>
            <option v-for="point in pickupPoints" :key="point.id" :value="point.id">
              {{ point.title || point.address }} - {{ point.address }}
            </option>
          </select>
        </label>

        <label v-if="isYandexNdd">
          Search pickup points
          <input v-model="pickupSearch" type="text" placeholder="Street, district, metro" />
        </label>

        <p v-if="selectedPickupPoint" class="selected-point">
          Selected: {{ selectedPickupPoint.title || selectedPickupPoint.address }} - {{ selectedPickupPoint.address }}
        </p>
      </div>

      <div v-if="showMap" class="map-wrapper">
        <div ref="deliveryMapEl" class="delivery-map"></div>
      </div>

      <p v-if="loadingMethods || loadingPickupPoints" class="state-box loading-note">
        Content loading...
      </p>

      <p v-else-if="!hasYandexMapsKey" class="map-hint">
        Map is hidden: set <code>VITE_YANDEX_MAPS_API_KEY</code> to enable Yandex Maps.
      </p>

      <p v-if="mapLoadError" class="state-box error">{{ mapLoadError }}</p>

      <label>
        Comment
        <textarea v-model="comment" rows="2" />
      </label>

      <div class="actions">
        <button
          type="button"
          class="btn btn-outline"
          :disabled="calculating || submittingConfirm || !canCalculate"
          @click="calculateDelivery"
        >
          Calculate delivery
        </button>
        <button
          type="button"
          class="btn btn-primary"
          :disabled="submittingConfirm || !preview"
          @click="confirmOrder"
        >
          Confirm order
        </button>
      </div>
    </form>

    <div v-if="cartStore.cart" class="summary surface-card">
      <div>Cart subtotal: {{ cartStore.cart.subtotal_original }} RUB</div>
      <div>Cart discount: -{{ cartStore.cart.discount_total }} RUB</div>
    </div>

    <div v-if="shippingOffers.length" class="summary offers surface-card">
      <div class="total">Available delivery offers</div>
      <div v-for="offer in shippingOffers" :key="offer.id" class="offer-row">
        <span>{{ offer.delivery_type }}</span>
        <span>{{ offer.price ?? "-" }} RUB</span>
        <span>
          {{ offer.date_interval?.from || "-" }}
          <template v-if="offer.date_interval?.to">- {{ offer.date_interval.to }}</template>
        </span>
      </div>
    </div>

    <div v-if="preview" class="summary surface-card">
      <div>Items total: {{ preview.items_total }} {{ preview.currency }}</div>
      <div>Shipping: {{ preview.shipping_price }} {{ preview.currency }}</div>
      <div class="total">Total: {{ preview.total }} {{ preview.currency }}</div>
    </div>

    <div v-if="error" class="state-box error">{{ error }}</div>
    <div v-if="success" class="state-box success">Order created. Redirecting to payment...</div>
  </section>
</template>

<script setup lang="ts">
import { computed, nextTick, onMounted, onUnmounted, ref, watch } from "vue";
import { useRouter } from "vue-router";

import {
  confirmCheckout,
  getCheckoutShippingMethods,
  getShippingPickupPoints,
  getShippingQuote,
  previewCheckout
} from "../api/public";
import { useAuthStore } from "../stores/auth";
import { useCartStore } from "../stores/cart";

declare global {
  interface Window {
    ymaps?: any;
  }
}

type ShippingMethod = {
  provider_id: string;
  title: string;
  is_sandbox: boolean;
};

type ShippingType = "pickup" | "courier";

type AddressDraft = {
  city: string;
  postal_code: string;
  street: string;
  house: string;
};

type PickupPoint = {
  id: string;
  title?: string;
  address: string;
  lat: number | null;
  lng: number | null;
  type?: string;
  work_time?: string;
};

type ShippingOffer = {
  id: string;
  delivery_type: string;
  price: number | null;
  date_interval?: {
    from?: string | null;
    to?: string | null;
  };
};

type PreviewPayload = {
  items_total: number;
  shipping_price: number;
  total: number;
  currency: string;
};

const router = useRouter();
const authStore = useAuthStore();
const cartStore = useCartStore();

const emptyAddress = (): AddressDraft => ({
  city: "",
  postal_code: "",
  street: "",
  house: ""
});

const cloneAddress = (value: AddressDraft): AddressDraft => ({
  city: String(value.city || ""),
  postal_code: String(value.postal_code || ""),
  street: String(value.street || ""),
  house: String(value.house || "")
});

const address = ref<AddressDraft>(emptyAddress());
const courierAddress = ref<AddressDraft>(emptyAddress());
const pickupAddress = ref<AddressDraft>(emptyAddress());
const shippingProvider = ref("");
const shippingType = ref<ShippingType>("courier");
const pickupPointId = ref("");
const pickupSearch = ref("");
const comment = ref("");

const shippingMethods = ref<ShippingMethod[]>([]);
const pickupPoints = ref<PickupPoint[]>([]);
const shippingOffers = ref<ShippingOffer[]>([]);
const preview = ref<PreviewPayload | null>(null);

const loadingMethods = ref(false);
const loadingPickupPoints = ref(false);
const calculating = ref(false);
const submittingConfirm = ref(false);
const success = ref(false);
const error = ref<string | null>(null);

const deliveryMapEl = ref<HTMLDivElement | null>(null);
const mapLoadError = ref<string | null>(null);

const MOSCOW_CENTER: [number, number] = [55.751244, 37.618423];
const yandexMapsApiKey = String(import.meta.env.VITE_YANDEX_MAPS_API_KEY || "").trim();
const hasYandexMapsKey = Boolean(yandexMapsApiKey);
const isYandexNdd = computed(() => shippingProvider.value === "yandex_ndd");
const showMap = computed(() => hasYandexMapsKey);

let yandexMapsLoader: Promise<any> | null = null;
let yandexMap: any = null;
let isSyncingAddress = false;
let courierGeocodeTimer: ReturnType<typeof setTimeout> | null = null;
let courierGeocodeRequestId = 0;
const courierCoords = ref<[number, number] | null>(null);

const selectedPickupPoint = computed(
  () => pickupPoints.value.find((point) => point.id === pickupPointId.value) || null
);

const canCalculate = computed(() => {
  if (!shippingProvider.value) return false;
  if (!address.value.city || !address.value.street || !address.value.house) {
    return false;
  }
  if (shippingType.value === "courier" && !address.value.postal_code) {
    return false;
  }
  if (shippingType.value === "pickup" && !pickupPointId.value) {
    return false;
  }
  return true;
});

const hasAnyAddressValue = (value: AddressDraft) =>
  Boolean(value.city || value.postal_code || value.street || value.house);

const setAddress = (value: AddressDraft) => {
  isSyncingAddress = true;
  address.value = cloneAddress(value);
  isSyncingAddress = false;
};

const normalizeWhitespace = (value: string) => String(value || "").replace(/\s+/g, " ").trim();

const parsePickupAddress = (rawAddress: string): AddressDraft => {
  const base = normalizeWhitespace(rawAddress);
  const postalMatch = base.match(/\b\d{6}\b/);
  const postalCode = postalMatch ? postalMatch[0] : "";

  const withoutPostal = normalizeWhitespace(base.replace(/\b\d{6}\b/g, "").replace(/\s*,\s*/g, ", "));
  const parts = withoutPostal
    .split(",")
    .map((part) => normalizeWhitespace(part))
    .filter(Boolean);

  const city = parts.length >= 2 ? parts[0] : address.value.city || pickupAddress.value.city || "Москва";
  const addressLine = normalizeWhitespace(parts.length >= 2 ? parts.slice(1).join(", ") : withoutPostal);

  const partsWithHouseHint = addressLine
    .split(",")
    .map((part) => normalizeWhitespace(part))
    .filter(Boolean);

  let street = addressLine;
  let house = "";

  const tokenWithDigitsIndex = partsWithHouseHint.findIndex((part) => /\d+/.test(part));
  if (tokenWithDigitsIndex > 0) {
    street = normalizeWhitespace(partsWithHouseHint.slice(0, tokenWithDigitsIndex).join(", "));
    house = partsWithHouseHint[tokenWithDigitsIndex];
  }

  if (!house) {
    const explicitHouseMatch = addressLine.match(/^(.*?)[,\s]+(?:дом|д\.?)?\s*(\d+[A-Za-zА-Яа-я0-9/-]*)\b/i);
    if (explicitHouseMatch) {
      street = normalizeWhitespace(explicitHouseMatch[1]);
      house = explicitHouseMatch[2] || "";
    }
  }

  street = normalizeWhitespace(street.replace(/(?:,?\s*(?:дом|д\.?))$/i, "").replace(/,+$/g, ""));
  const houseNumberMatch = house.match(/\d+/);

  return {
    city,
    postal_code: postalCode,
    street: street || addressLine,
    house: houseNumberMatch ? houseNumberMatch[0] : ""
  };
};

const applyPickupPointAddress = (point: PickupPoint) => {
  const parsed = parsePickupAddress(point.address || "");
  const nextAddress: AddressDraft = {
    city: parsed.city || address.value.city || pickupAddress.value.city,
    postal_code: parsed.postal_code || pickupAddress.value.postal_code || address.value.postal_code,
    street: parsed.street || address.value.street,
    house: parsed.house || address.value.house
  };

  setAddress(nextAddress);
  pickupAddress.value = cloneAddress(nextAddress);
};

const loadYandexMaps = async () => {
  if (!hasYandexMapsKey) {
    throw new Error("Yandex Maps API key is not configured.");
  }

  if (window.ymaps) {
    await window.ymaps.ready();
    return window.ymaps;
  }

  if (!yandexMapsLoader) {
    yandexMapsLoader = new Promise((resolve, reject) => {
      const existingScript = document.getElementById("yandex-maps-api");
      if (existingScript) {
        existingScript.addEventListener("load", async () => {
          try {
            await window.ymaps?.ready();
            resolve(window.ymaps);
          } catch (err) {
            reject(err);
          }
        });
        existingScript.addEventListener("error", () => reject(new Error("Failed to load Yandex Maps script.")));
        return;
      }

      const script = document.createElement("script");
      script.id = "yandex-maps-api";
      script.async = true;
      script.src = `https://api-maps.yandex.ru/2.1/?apikey=${encodeURIComponent(yandexMapsApiKey)}&lang=ru_RU`;
      script.onload = async () => {
        try {
          await window.ymaps?.ready();
          resolve(window.ymaps);
        } catch (err) {
          reject(err);
        }
      };
      script.onerror = () => reject(new Error("Failed to load Yandex Maps script."));
      document.head.appendChild(script);
    });
  }

  return yandexMapsLoader;
};

const clearMap = () => {
  if (yandexMap) {
    yandexMap.destroy();
    yandexMap = null;
  }
};

const ensureMap = async () => {
  if (!showMap.value || !deliveryMapEl.value) {
    return null;
  }

  const ymaps = await loadYandexMaps();

  if (!yandexMap) {
    yandexMap = new ymaps.Map(deliveryMapEl.value, {
      center: MOSCOW_CENTER,
      zoom: 10,
      controls: ["zoomControl", "typeSelector"]
    });
  }

  return ymaps;
};

const renderPickupPointsOnMap = (ymaps: any) => {
  const pointsWithCoords = pickupPoints.value.filter(
    (point) => typeof point.lat === "number" && typeof point.lng === "number"
  );

  pointsWithCoords.forEach((point) => {
    const isSelected = point.id === pickupPointId.value;
    const placemark = new ymaps.Placemark(
      [point.lat, point.lng],
      {
        hintContent: point.title || point.address,
        balloonContentHeader: point.title || "Pickup point",
        balloonContentBody: point.address
      },
      {
        preset: isSelected ? "islands#greenIcon" : "islands#blueIcon"
      }
    );

    placemark.events.add("click", () => {
      pickupPointId.value = point.id;
      error.value = null;
    });

    yandexMap.geoObjects.add(placemark);
  });

  if (selectedPickupPoint.value && typeof selectedPickupPoint.value.lat === "number" && typeof selectedPickupPoint.value.lng === "number") {
    yandexMap.setCenter([selectedPickupPoint.value.lat, selectedPickupPoint.value.lng], 12, {
      duration: 200
    });
    return;
  }

  if (pointsWithCoords.length > 0) {
    const first = pointsWithCoords[0];
    yandexMap.setCenter([first.lat as number, first.lng as number], 10, { duration: 200 });
  } else {
    yandexMap.setCenter(MOSCOW_CENTER, 10, { duration: 200 });
  }
};

const renderCourierAddressOnMap = (ymaps: any) => {
  if (courierCoords.value) {
    const placemark = new ymaps.Placemark(
      courierCoords.value,
      {
        hintContent: "Courier address",
        balloonContent: `${address.value.city}, ${address.value.street}, ${address.value.house}`
      },
      {
        preset: "islands#redIcon"
      }
    );
    yandexMap.geoObjects.add(placemark);
    yandexMap.setCenter(courierCoords.value, 13, { duration: 200 });
    return;
  }

  yandexMap.setCenter(MOSCOW_CENTER, 10, { duration: 200 });
};

const renderMap = async () => {
  if (!showMap.value || !deliveryMapEl.value) {
    return;
  }

  const ymaps = await ensureMap();
  if (!ymaps || !yandexMap) {
    return;
  }

  yandexMap.geoObjects.removeAll();

  if (shippingType.value === "pickup") {
    renderPickupPointsOnMap(ymaps);
    return;
  }

  renderCourierAddressOnMap(ymaps);
};

const buildCourierAddressQuery = () => {
  const parts = [address.value.city, address.value.street, address.value.house]
    .map((part) => normalizeWhitespace(part))
    .filter(Boolean);
  return parts.join(", ");
};

const geocodeCourierAddress = async () => {
  if (!showMap.value || shippingType.value !== "courier") {
    return;
  }

  const query = buildCourierAddressQuery();
  if (!query) {
    courierCoords.value = null;
    await renderMap();
    return;
  }

  const requestId = ++courierGeocodeRequestId;

  try {
    const ymaps = await loadYandexMaps();
    const geoResult = await ymaps.geocode(query, { results: 1 });
    if (requestId !== courierGeocodeRequestId) {
      return;
    }

    const first = geoResult.geoObjects.get(0);
    if (!first) {
      courierCoords.value = null;
      await renderMap();
      return;
    }

    const coordinates = first.geometry?.getCoordinates?.();
    if (Array.isArray(coordinates) && coordinates.length === 2) {
      const lat = Number(coordinates[0]);
      const lng = Number(coordinates[1]);
      if (Number.isFinite(lat) && Number.isFinite(lng)) {
        courierCoords.value = [lat, lng];
      } else {
        courierCoords.value = null;
      }
    } else {
      courierCoords.value = null;
    }

    mapLoadError.value = null;
    await renderMap();
  } catch {
    if (requestId !== courierGeocodeRequestId) {
      return;
    }

    courierCoords.value = null;
    mapLoadError.value = "Failed to resolve courier address on map. You can continue with text fields.";

    try {
      await renderMap();
    } catch {
      // Ignore secondary render errors.
    }
  }
};

const scheduleCourierGeocode = () => {
  if (!showMap.value || shippingType.value !== "courier") {
    return;
  }

  if (courierGeocodeTimer) {
    clearTimeout(courierGeocodeTimer);
  }

  courierGeocodeTimer = setTimeout(() => {
    void geocodeCourierAddress();
  }, 450);
};

const loadShippingMethods = async () => {
  loadingMethods.value = true;
  error.value = null;
  try {
    const response = await getCheckoutShippingMethods();
    shippingMethods.value = response.data?.results || [];
    if (shippingMethods.value.length > 0 && !shippingProvider.value) {
      shippingProvider.value = shippingMethods.value[0].provider_id;
    }
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to load shipping methods.";
  } finally {
    loadingMethods.value = false;
  }
};

const loadPickupPoints = async () => {
  if (shippingType.value !== "pickup") {
    return;
  }

  if (!shippingProvider.value || !address.value.city) {
    pickupPoints.value = [];
    pickupPointId.value = "";
    if (showMap.value) {
      await renderMap();
    }
    return;
  }

  const currentPickupPointId = pickupPointId.value;
  pickupPoints.value = [];
  loadingPickupPoints.value = true;
  error.value = null;
  mapLoadError.value = null;

  try {
    const response = await getShippingPickupPoints(
      shippingProvider.value,
      address.value.city,
      isYandexNdd.value ? pickupSearch.value : undefined
    );
    const payload = response.data;
    const points = Array.isArray(payload) ? payload : payload?.results || [];
    pickupPoints.value = points;

    if (currentPickupPointId && points.some((point: PickupPoint) => point.id === currentPickupPointId)) {
      pickupPointId.value = currentPickupPointId;
    } else {
      pickupPointId.value = "";
    }

    if (selectedPickupPoint.value) {
      applyPickupPointAddress(selectedPickupPoint.value);
    }

    if (showMap.value) {
      await nextTick();
      try {
        await renderMap();
      } catch {
        mapLoadError.value = "Failed to load Yandex map. You can still select pickup point from dropdown.";
      }
    }
  } catch (err: any) {
    error.value = err?.response?.data?.detail || "Failed to load pickup points.";
    mapLoadError.value = hasYandexMapsKey ? "Map is unavailable right now." : null;
  } finally {
    loadingPickupPoints.value = false;
  }
};

const checkoutPayload = () => ({
  address: { ...address.value },
  shipping_provider: shippingProvider.value,
  shipping_type: shippingType.value,
  pickup_point_id: shippingType.value === "pickup" ? pickupPointId.value : undefined,
  comment: comment.value
});

const quotePayload = () => ({
  address: { ...address.value },
  shipping_type: shippingType.value,
  pickup_point_id: shippingType.value === "pickup" ? pickupPointId.value : undefined,
  comment: comment.value
});

const calculateDelivery = async () => {
  if (!canCalculate.value) {
    if (shippingType.value === "pickup" && !pickupPointId.value) {
      error.value = "Select pickup point to continue.";
      return;
    }
    if (shippingType.value === "courier" && !address.value.postal_code) {
      error.value = "Postal code is required for courier delivery.";
    }
    return;
  }

  calculating.value = true;
  error.value = null;

  try {
    if (isYandexNdd.value) {
      const quoteResponse = await getShippingQuote(shippingProvider.value, quotePayload());
      shippingOffers.value = quoteResponse.data?.offers || [];
    } else {
      shippingOffers.value = [];
    }

    const response = await previewCheckout(checkoutPayload());
    preview.value = response.data as PreviewPayload;
  } catch (err: any) {
    const data = err?.response?.data;
    error.value = data?.detail || Object.values(data || {})?.[0]?.[0] || "Failed to calculate delivery.";
    preview.value = null;
    shippingOffers.value = [];
  } finally {
    calculating.value = false;
  }
};

const confirmOrder = async () => {
  if (!preview.value) {
    return;
  }

  if (shippingType.value === "pickup" && !pickupPointId.value) {
    error.value = "Select pickup point before confirming the order.";
    return;
  }

  submittingConfirm.value = true;
  error.value = null;
  try {
    const response = await confirmCheckout(checkoutPayload());
    const data = response.data || {};
    const orderNumber = String(data.order_number || "");
    const orderSecret = String(data.order_secret || "");

    if (!authStore.token) {
      localStorage.setItem("guestOrderNumber", orderNumber);
      localStorage.setItem("guestOrderSecret", orderSecret);
    }

    success.value = true;
    await cartStore.fetchCart();

    const query: Record<string, string> = { order_number: orderNumber };
    if (!authStore.token && orderSecret) {
      query.order_secret = orderSecret;
    }
    await router.push({ path: "/pay", query });
  } catch (err: any) {
    const data = err?.response?.data;
    error.value = data?.detail || Object.values(data || {})?.[0]?.[0] || "Failed to confirm order.";
  } finally {
    submittingConfirm.value = false;
  }
};

watch(
  [() => address.value.city, () => address.value.postal_code, () => address.value.street, () => address.value.house],
  () => {
    preview.value = null;
    shippingOffers.value = [];

    if (!isSyncingAddress) {
      if (shippingType.value === "courier") {
        courierAddress.value = cloneAddress(address.value);
      } else {
        pickupAddress.value = cloneAddress(address.value);
      }
    }

    if (shippingType.value === "courier") {
      scheduleCourierGeocode();
    }
  }
);

watch(shippingType, async (nextType, previousType) => {
  preview.value = null;
  shippingOffers.value = [];
  mapLoadError.value = null;

  if (previousType === "courier") {
    courierAddress.value = cloneAddress(address.value);
  }
  if (previousType === "pickup") {
    pickupAddress.value = cloneAddress(address.value);
  }

  if (nextType === "pickup") {
    if (hasAnyAddressValue(pickupAddress.value)) {
      setAddress(pickupAddress.value);
    }

    await loadPickupPoints();
    if (selectedPickupPoint.value) {
      applyPickupPointAddress(selectedPickupPoint.value);
    }

    if (showMap.value) {
      try {
        await nextTick();
        await renderMap();
      } catch {
        mapLoadError.value = "Failed to load Yandex map. You can still select pickup point from dropdown.";
      }
    }
    return;
  }

  if (hasAnyAddressValue(courierAddress.value)) {
    setAddress(courierAddress.value);
  }

  if (showMap.value) {
    scheduleCourierGeocode();
  }
});

watch([shippingProvider, () => address.value.city, pickupSearch], async () => {
  preview.value = null;
  shippingOffers.value = [];

  if (shippingType.value === "pickup") {
    await loadPickupPoints();
    return;
  }

  if (shippingType.value === "courier") {
    scheduleCourierGeocode();
  }
});

watch(pickupPointId, async () => {
  preview.value = null;
  shippingOffers.value = [];

  if (shippingType.value === "pickup" && selectedPickupPoint.value) {
    applyPickupPointAddress(selectedPickupPoint.value);
    error.value = null;
  }

  if (!showMap.value) {
    return;
  }

  try {
    await renderMap();
  } catch {
    mapLoadError.value = "Failed to update map. Dropdown selection still works.";
  }
});

watch(showMap, async (enabled) => {
  mapLoadError.value = null;
  if (!enabled) {
    clearMap();
    return;
  }

  try {
    await nextTick();
    if (shippingType.value === "pickup") {
      await renderMap();
    } else {
      scheduleCourierGeocode();
    }
  } catch {
    mapLoadError.value = "Failed to load Yandex map.";
  }
});

onMounted(async () => {
  await cartStore.fetchCart();
  await loadShippingMethods();
  if (shippingType.value === "pickup") {
    await loadPickupPoints();
  }
  if (showMap.value && shippingType.value === "courier") {
    scheduleCourierGeocode();
  }
});

onUnmounted(() => {
  if (courierGeocodeTimer) {
    clearTimeout(courierGeocodeTimer);
  }
  clearMap();
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
  max-width: 640px;
  padding: 14px;
}

label {
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.mode-field {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.mode-label {
  font-size: 14px;
  color: var(--text);
}

.mode-switch {
  display: inline-flex;
  width: fit-content;
  border: 1px solid var(--border);
  border-radius: 11px;
  overflow: hidden;
}

.mode-button {
  border: 0;
  min-height: 40px;
  padding: 8px 16px;
  cursor: pointer;
  border-radius: 0;
  background: color-mix(in srgb, var(--surface) 82%, var(--border));
  color: var(--text);
}

.mode-button.active {
  background: var(--primary);
  color: var(--primary-contrast);
}

.mode-button:disabled {
  opacity: 0.7;
  cursor: not-allowed;
}

.pickup-block {
  display: flex;
  flex-direction: column;
  gap: 10px;
}

.selected-point {
  margin: 0;
  font-size: 14px;
  color: var(--text);
}

.map-wrapper {
  border: 1px solid var(--border);
  border-radius: 14px;
  background: var(--surface);
  overflow: hidden;
}

.loading-note {
  max-width: 640px;
}

.delivery-map {
  width: 100%;
  height: 320px;
}

.map-hint {
  margin: 0;
  color: var(--muted);
}

.actions {
  display: flex;
  gap: 10px;
  flex-wrap: wrap;
}

.summary {
  max-width: 640px;
  display: flex;
  flex-direction: column;
  gap: 6px;
  padding: 12px;
}

.summary .total {
  font-weight: 700;
}

.offer-row {
  display: grid;
  grid-template-columns: 1fr auto;
  gap: 4px 8px;
  border-top: 1px solid var(--border);
  padding-top: 6px;
}

@media (max-width: 700px) {
  .delivery-map {
    height: 260px;
  }

  .actions {
    flex-wrap: wrap;
  }
}
</style>
