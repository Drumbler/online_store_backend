<template>
  <section class="page">
    <header class="heading">
      <div>
        <h1>Reports</h1>
        <p>Отчёты по месяцам и за календарный год.</p>
      </div>
      <div class="mode-actions">
        <button
          type="button"
          class="mode-btn"
          :class="{ active: mode === 'monthly' }"
          :disabled="loading || downloading || !hasPeriods"
          @click="setMode('monthly')"
        >
          Отчетность за месяц
        </button>
        <button
          type="button"
          class="mode-btn"
          :class="{ active: mode === 'yearly' }"
          :disabled="loading || downloading || !hasPeriods"
          @click="setMode('yearly')"
        >
          Отчетность за год
        </button>
      </div>
    </header>

    <p v-if="error" class="error">{{ error }}</p>

    <div v-if="hasPeriods" class="filters">
      <label>
        <span>Год</span>
        <select v-model.number="selectedYear" :disabled="loading || downloading">
          <option v-for="year in years" :key="year" :value="year">{{ year }}</option>
        </select>
      </label>

      <label v-if="mode === 'monthly'">
        <span>Месяц</span>
        <select v-model.number="selectedMonth" :disabled="loading || downloading || monthOptions.length === 0">
          <option v-for="month in monthOptions" :key="month" :value="month">
            {{ monthLabel(month) }}
          </option>
        </select>
      </label>

      <button type="button" :disabled="loading || downloading || !canBuildReport" @click="loadReport">
        Показать
      </button>

      <button type="button" :disabled="loading || downloading || !canBuildReport" @click="downloadExcel">
        Выгрузить Excel
      </button>
    </div>

    <p v-else class="empty-periods">Нет записанных периодов в БД.</p>

    <div v-if="loading" class="loading">Loading report...</div>

    <template v-else>
      <p class="period">Период: {{ periodLabel }}</p>

      <div class="table-wrap">
        <table class="table">
          <thead>
            <tr>
              <th>Название товара</th>
              <th>Просмотры</th>
              <th>Продано</th>
              <th>Выручка</th>
            </tr>
          </thead>
          <tbody>
            <tr class="total-row">
              <td>ИТОГО</td>
              <td>{{ totals.views }}</td>
              <td>{{ totals.units_sold }}</td>
              <td>{{ totals.revenue }}</td>
            </tr>
            <tr v-for="row in rows" :key="row.product_id">
              <td>{{ row.title }}</td>
              <td>{{ row.views }}</td>
              <td>{{ row.units_sold }}</td>
              <td>{{ row.revenue }}</td>
            </tr>
            <tr v-if="rows.length === 0">
              <td colspan="4" class="empty">Нет данных за выбранный период.</td>
            </tr>
          </tbody>
        </table>
      </div>
    </template>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref, watch } from "vue";

import { adminApiClient } from "../api/adminClient";

type ReportMode = "monthly" | "yearly";

type ReportRow = {
  product_id: string;
  title: string;
  views: number;
  units_sold: number;
  revenue: string;
};

type ReportPayload = {
  period: {
    from: string;
    to: string;
  };
  totals: {
    views: number;
    units_sold: number;
    revenue: string;
  };
  results: ReportRow[];
};

type PeriodsPayload = {
  years: number[];
  months_by_year: Record<string, number[]>;
};

const loading = ref(false);
const downloading = ref(false);
const error = ref<string | null>(null);

const mode = ref<ReportMode>("monthly");
const years = ref<number[]>([]);
const monthsByYear = ref<Record<string, number[]>>({});

const selectedYear = ref<number | null>(null);
const selectedMonth = ref<number | null>(null);

const period = ref({ from: "", to: "" });
const totals = ref({ views: 0, units_sold: 0, revenue: "0.00" });
const rows = ref<ReportRow[]>([]);

const hasPeriods = computed(() => years.value.length > 0);

const monthOptions = computed(() => {
  if (!selectedYear.value) {
    return [];
  }
  return monthsByYear.value[String(selectedYear.value)] || [];
});

const canBuildReport = computed(() => {
  if (!selectedYear.value) {
    return false;
  }
  if (mode.value === "monthly" && !selectedMonth.value) {
    return false;
  }
  return true;
});

const periodLabel = computed(() => {
  if (!period.value.from || !period.value.to) {
    return "—";
  }
  return `${period.value.from} — ${period.value.to}`;
});

const monthLabel = (month: number) => {
  const date = new Date(2000, month - 1, 1);
  return date.toLocaleString("ru-RU", { month: "long" });
};

const resetReportData = () => {
  period.value = { from: "", to: "" };
  totals.value = { views: 0, units_sold: 0, revenue: "0.00" };
  rows.value = [];
};

const parseErrorText = (text: string, fallback: string) => {
  if (!text) {
    return fallback;
  }
  try {
    const parsed = JSON.parse(text);
    if (typeof parsed?.detail === "string" && parsed.detail) {
      return parsed.detail;
    }
  } catch {
    // Response is not JSON. Return plain text as-is.
  }
  return text;
};

const extractApiError = async (err: any, fallback: string) => {
  const responseData = err?.response?.data;
  if (!responseData) {
    return fallback;
  }
  if (typeof responseData?.detail === "string" && responseData.detail) {
    return responseData.detail;
  }
  if (typeof responseData === "string") {
    return parseErrorText(responseData, fallback);
  }
  if (typeof Blob !== "undefined" && responseData instanceof Blob) {
    try {
      const text = await responseData.text();
      return parseErrorText(text, fallback);
    } catch {
      return fallback;
    }
  }
  return fallback;
};

const loadPeriods = async () => {
  error.value = null;
  try {
    const response = await adminApiClient.get<PeriodsPayload>("/admin/reports/periods/");
    const payload = response.data;
    years.value = payload.years || [];
    monthsByYear.value = payload.months_by_year || {};

    if (years.value.length === 0) {
      selectedYear.value = null;
      selectedMonth.value = null;
      resetReportData();
      return;
    }

    selectedYear.value = years.value[0];
    const months = monthsByYear.value[String(selectedYear.value)] || [];
    selectedMonth.value = months.length > 0 ? months[months.length - 1] : null;
  } catch (err: any) {
    error.value = await extractApiError(err, "Failed to load available periods.");
    years.value = [];
    monthsByYear.value = {};
    selectedYear.value = null;
    selectedMonth.value = null;
    resetReportData();
  }
};

const reportRequestConfig = () => {
  if (!selectedYear.value) {
    return null;
  }

  if (mode.value === "yearly") {
    return {
      jsonPath: "/admin/reports/yearly/",
      xlsxPath: "/admin/reports/yearly.xlsx",
      params: { year: selectedYear.value }
    };
  }

  if (!selectedMonth.value) {
    return null;
  }

  return {
    jsonPath: "/admin/reports/monthly/",
    xlsxPath: "/admin/reports/monthly.xlsx",
    params: { year: selectedYear.value, month: selectedMonth.value }
  };
};

const loadReport = async () => {
  const config = reportRequestConfig();
  if (!config) {
    return;
  }

  loading.value = true;
  error.value = null;
  try {
    const response = await adminApiClient.get<ReportPayload>(config.jsonPath, {
      params: config.params
    });
    const payload = response.data;
    period.value = payload.period || { from: "", to: "" };
    totals.value = payload.totals || { views: 0, units_sold: 0, revenue: "0.00" };
    rows.value = payload.results || [];
  } catch (err: any) {
    error.value = await extractApiError(err, "Failed to load report.");
    resetReportData();
  } finally {
    loading.value = false;
  }
};

const parseFilename = (contentDisposition?: string) => {
  if (!contentDisposition) {
    return "report.xlsx";
  }
  const utfMatch = contentDisposition.match(/filename\*=UTF-8''([^;]+)/i);
  if (utfMatch?.[1]) {
    return decodeURIComponent(utfMatch[1]);
  }
  const simpleMatch = contentDisposition.match(/filename="?([^";]+)"?/i);
  if (simpleMatch?.[1]) {
    return simpleMatch[1];
  }
  return "report.xlsx";
};

const downloadExcel = async () => {
  const config = reportRequestConfig();
  if (!config) {
    return;
  }

  downloading.value = true;
  error.value = null;
  try {
    const response = await adminApiClient.get(config.xlsxPath, {
      params: config.params,
      responseType: "blob"
    });
    const blob = new Blob([response.data], {
      type: "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
    });
    const url = window.URL.createObjectURL(blob);
    const link = document.createElement("a");
    link.href = url;
    link.download = parseFilename(response.headers["content-disposition"]);
    document.body.appendChild(link);
    link.click();
    link.remove();
    window.URL.revokeObjectURL(url);
  } catch (err: any) {
    error.value = await extractApiError(err, "Failed to download Excel file.");
  } finally {
    downloading.value = false;
  }
};

const setMode = async (nextMode: ReportMode) => {
  mode.value = nextMode;
  await loadReport();
};

watch(selectedYear, (year) => {
  if (!year) {
    selectedMonth.value = null;
    return;
  }
  const months = monthsByYear.value[String(year)] || [];
  if (months.length === 0) {
    selectedMonth.value = null;
    return;
  }
  if (!selectedMonth.value || !months.includes(selectedMonth.value)) {
    selectedMonth.value = months[months.length - 1];
  }
});

onMounted(async () => {
  await loadPeriods();
  await loadReport();
});
</script>

<style scoped>
.page {
  display: flex;
  flex-direction: column;
  gap: 16px;
}

.heading {
  display: flex;
  align-items: flex-end;
  justify-content: space-between;
  gap: 16px;
}

.heading p {
  color: #6f5f4c;
  margin: 4px 0 0;
}

.mode-actions {
  display: flex;
  gap: 8px;
  flex-wrap: wrap;
}

.mode-btn {
  border: 1px solid #c6b59a;
  background: #f6efe1;
  color: #4b3c2f;
  padding: 8px 12px;
  cursor: pointer;
}

.mode-btn.active {
  background: #e7d6bc;
  font-weight: 600;
}

.filters {
  display: flex;
  align-items: end;
  gap: 10px;
  flex-wrap: wrap;
}

.filters label {
  display: flex;
  flex-direction: column;
  gap: 6px;
}

.period {
  margin: 0;
  color: #5f503f;
}

.error {
  color: #b11e1e;
  margin: 0;
}

.loading {
  padding: 16px;
  border: 1px dashed #c6b59a;
  background: #fffdf8;
}

.empty-periods {
  margin: 0;
  color: #6f5f4c;
}

.table-wrap {
  overflow-x: auto;
  background: #fffdf8;
  border: 1px solid #e2d5be;
}

.table {
  width: 100%;
  border-collapse: collapse;
}

.table th,
.table td {
  padding: 12px;
  border-bottom: 1px solid #eadfc9;
  text-align: left;
  white-space: nowrap;
}

.table th {
  background: #f3ead8;
  font-weight: 600;
}

.total-row td {
  font-weight: 700;
  background: #f9f1e3;
}

.table tr:last-child td {
  border-bottom: none;
}

.empty {
  text-align: center;
  color: #6f5f4c;
}
</style>
