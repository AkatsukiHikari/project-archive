<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="利用台账"
      description="档案利用统计报表：按月 / 季 / 年看利用趋势、利用方式与查档目的分布、各门类利用情况"
      icon="heroicons:chart-bar"
    />

    <!-- 控制条 -->
    <div class="pro-card p-4 flex flex-wrap items-end gap-3">
      <div class="flex flex-col gap-1">
        <span class="text-xs text-gray-500">统计粒度</span>
        <NRadioGroup v-model:value="granularity" size="small" @update:value="load">
          <NRadioButton value="month">按月</NRadioButton>
          <NRadioButton value="quarter">按季度</NRadioButton>
          <NRadioButton value="year">按年度</NRadioButton>
        </NRadioGroup>
      </div>
      <div class="flex flex-col gap-1">
        <span class="text-xs text-gray-500">统计区间</span>
        <NDatePicker
          v-model:value="dateRange"
          type="daterange"
          clearable
          :shortcuts="shortcuts"
          format="yyyy-MM-dd"
          style="width: 300px"
          @update:value="load"
        />
      </div>
      <NButton type="primary" :loading="loading" @click="load">
        <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
        统计
      </NButton>
    </div>

    <!-- KPI -->
    <div class="grid grid-cols-3 gap-4">
      <StatCard label="利用件次" :value="stats?.summary.items ?? 0" icon="heroicons:document-magnifying-glass" tone="blue" />
      <StatCard label="利用人次" :value="stats?.summary.applications ?? 0" icon="heroicons:user-group" tone="violet" />
      <StatCard label="涉及档案数" :value="stats?.summary.archives ?? 0" icon="heroicons:folder" tone="green" />
    </div>

    <!-- 图表 -->
    <div class="pro-card p-5 flex flex-col gap-2">
      <p class="text-sm font-medium">利用趋势（点击柱可查看该时期明细）</p>
      <EChart :option="trendOption" :height="280" @chart-click="onTrendClick" />
    </div>

    <div class="grid grid-cols-1 lg:grid-cols-3 gap-4">
      <div class="pro-card p-5 flex flex-col gap-2">
        <p class="text-sm font-medium">利用方式分布</p>
        <EChart :option="useTypeOption" :height="260" />
      </div>
      <div class="pro-card p-5 flex flex-col gap-2">
        <p class="text-sm font-medium">查档目的分布</p>
        <EChart :option="purposeOption" :height="260" />
      </div>
      <div class="pro-card p-5 flex flex-col gap-2">
        <p class="text-sm font-medium">各门类利用情况</p>
        <EChart :option="categoryOption" :height="260" />
      </div>
    </div>

    <!-- 期间明细抽屉 -->
    <NDrawer v-model:show="showDetail" :width="720" placement="right">
      <NDrawerContent :title="`利用明细 · ${detailPeriod}`" closable>
        <div class="flex items-center justify-between mb-2">
          <span class="text-sm text-gray-500">共 {{ detailRows.length }} 条</span>
          <NButton size="small" tertiary :disabled="!detailRows.length" @click="exportDetail">导出 CSV</NButton>
        </div>
        <ProTable :columns="detailColumns" :data="detailRows" :loading="detailLoading" :page-size="0" size="small" />
      </NDrawerContent>
    </NDrawer>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted, h } from "vue";
import { NRadioGroup, NRadioButton, NDatePicker, NButton, NDrawer, NDrawerContent, useMessage } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable, EChart } from "@/components/ui";
import { UtilizationAPI } from "@/api/utilization";
import type { LedgerStats, UtilLedgerRow } from "@/api/utilization";
import { CategoryAPI } from "@/api/repository";
import type { ArchiveCategory } from "@/api/repository";

definePageMeta({
  layout: "service",
  middleware: "auth",
  breadcrumb: [
    { name: "利用服务中心", path: "/service" },
    { name: "利用台账", path: "/service/ledger" },
  ],
});

const message = useMessage();
const PALETTE = ["#2563eb", "#7c3aed", "#0891b2", "#059669", "#d97706", "#db2777", "#dc2626", "#4f46e5"];
const USE_TYPE_LABEL: Record<string, string> = { read: "查阅", borrow: "借阅", copy: "复制", certificate: "出具证明" };
const pad = (n: number) => String(n).padStart(2, "0");

const granularity = ref<"month" | "quarter" | "year">("month");
const year = new Date().getFullYear();
// daterange picker 值为 [起始时间戳, 结束时间戳]
const dateRange = ref<[number, number] | null>([
  new Date(year, 0, 1).getTime(),
  new Date(year, 11, 31).getTime(),
]);

const toYmd = (ts: number): string => {
  const d = new Date(ts);
  return `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
};

const shortcuts = {
  本月: (): [number, number] => {
    const n = new Date();
    return [new Date(n.getFullYear(), n.getMonth(), 1).getTime(), new Date(n.getFullYear(), n.getMonth() + 1, 0).getTime()];
  },
  本季度: (): [number, number] => {
    const n = new Date(), q = Math.floor(n.getMonth() / 3);
    return [new Date(n.getFullYear(), q * 3, 1).getTime(), new Date(n.getFullYear(), q * 3 + 3, 0).getTime()];
  },
  本年: (): [number, number] => {
    const y = new Date().getFullYear();
    return [new Date(y, 0, 1).getTime(), new Date(y, 11, 31).getTime()];
  },
  近一年: (): [number, number] => [Date.now() - 365 * 86400000, Date.now()],
};

const loading = ref(false);
const stats = ref<LedgerStats | null>(null);
const categoryMap = ref<Record<string, string>>({});

async function load() {
  loading.value = true;
  try {
    stats.value = (await UtilizationAPI.ledgerStats({
      granularity: granularity.value,
      date_from: dateRange.value ? toYmd(dateRange.value[0]) : undefined,
      date_to: dateRange.value ? toYmd(dateRange.value[1]) : undefined,
    })).data;
  } finally {
    loading.value = false;
  }
}

// ── KPI 卡 ────────────────────────────────────────────────────────
const TONES: Record<string, string> = {
  blue: "text-blue-600 bg-blue-50", violet: "text-violet-600 bg-violet-50", green: "text-green-600 bg-green-50",
};
const resolveIcon = resolveComponent("Icon");
const StatCard = (props: { label: string; value: number; icon: string; tone: string }) =>
  h("div", { class: "pro-card p-4 flex items-center gap-3" }, [
    h("div", { class: `w-10 h-10 rounded-lg flex items-center justify-center ${TONES[props.tone] ?? TONES.blue}` }, [h(resolveIcon, { name: props.icon, class: "w-5 h-5" })]),
    h("div", { class: "flex flex-col" }, [
      h("span", { class: "text-xl font-bold tabular-nums" }, String(props.value)),
      h("span", { class: "text-xs text-gray-500" }, props.label),
    ]),
  ]);

// ── 图表 option ───────────────────────────────────────────────────
const axisCommon = {
  axisLabel: { color: "#94a3b8", fontSize: 11 },
  axisLine: { lineStyle: { color: "#e2e8f0" } },
  axisTick: { show: false },
};

const trendOption = computed(() => {
  const d = stats.value?.by_period ?? [];
  return {
    tooltip: { trigger: "axis" },
    grid: { top: 16, right: 16, bottom: 28, left: 40 },
    xAxis: { type: "category", data: d.map((x) => x.period), ...axisCommon, axisLabel: { ...axisCommon.axisLabel, rotate: d.length > 8 ? 35 : 0 } },
    yAxis: { type: "value", ...axisCommon, splitLine: { lineStyle: { color: "#f1f5f9" } } },
    series: [{ type: "bar", data: d.map((x) => x.count), itemStyle: { color: "#2563eb", borderRadius: [4, 4, 0, 0] }, barMaxWidth: 36 }],
  };
});

function pie(data: { name: string; value: number }[]) {
  return {
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: { bottom: 0, textStyle: { fontSize: 11, color: "#64748b" } },
    color: PALETTE,
    series: [{
      type: "pie", radius: ["42%", "66%"], center: ["50%", "44%"], avoidLabelOverlap: true,
      label: { show: false }, data,
    }],
  };
}
const useTypeOption = computed(() => pie((stats.value?.by_use_type ?? []).map((x) => ({ name: USE_TYPE_LABEL[x.name] ?? x.name, value: x.count }))));
const purposeOption = computed(() => pie((stats.value?.by_purpose ?? []).map((x) => ({ name: x.name, value: x.count }))));

const categoryOption = computed(() => {
  const d = (stats.value?.by_category ?? []).slice(0, 10).reverse();
  return {
    tooltip: { trigger: "axis", axisPointer: { type: "shadow" } },
    grid: { top: 8, right: 20, bottom: 8, left: 8, containLabel: true },
    xAxis: { type: "value", ...axisCommon, splitLine: { lineStyle: { color: "#f1f5f9" } } },
    yAxis: { type: "category", data: d.map((x) => (x.category_id === "未分类" ? "未分类" : categoryMap.value[x.category_id] ?? x.category_id.slice(0, 6))), ...axisCommon },
    series: [{ type: "bar", data: d.map((x) => x.count), itemStyle: { color: "#0891b2", borderRadius: [0, 4, 4, 0] }, barMaxWidth: 18 }],
  };
});

// ── 期间明细（下钻） ──────────────────────────────────────────────
const showDetail = ref(false);
const detailPeriod = ref("");
const detailLoading = ref(false);
const detailRows = ref<UtilLedgerRow[]>([]);

function periodRange(period: string): { from: string; to: string } {
  if (granularity.value === "year") return { from: `${period}-01-01`, to: `${period}-12-31` };
  if (granularity.value === "quarter") {
    const [y, q] = period.split("-Q");
    const sm = (Number(q) - 1) * 3 + 1, em = Number(q) * 3;
    return { from: `${y}-${pad(sm)}-01`, to: `${y}-${pad(em)}-${new Date(Number(y), em, 0).getDate()}` };
  }
  const [y, m] = period.split("-");
  return { from: `${period}-01`, to: `${period}-${new Date(Number(y), Number(m), 0).getDate()}` };
}

async function onTrendClick(p: { name: string }) {
  if (!p.name) return;
  const { from, to } = periodRange(p.name);
  detailPeriod.value = p.name;
  showDetail.value = true;
  detailLoading.value = true;
  try {
    detailRows.value = (await UtilizationAPI.ledger({ date_from: from, date_to: to })).data;
  } finally {
    detailLoading.value = false;
  }
}

const fmt = (s?: string | null) => (s ? s.replace("T", " ").slice(0, 16) : "—");
const detailColumns: DataTableColumns<UtilLedgerRow> = [
  { title: "序号", key: "_idx", width: 56, render: (_r, i) => i + 1 },
  { title: "利用日期", key: "used_at", width: 140, render: (r) => fmt(r.used_at) },
  { title: "利用人", key: "applicant_name", width: 90 },
  { title: "利用方式", key: "use_type", width: 80, render: (r) => USE_TYPE_LABEL[r.use_type] ?? r.use_type },
  { title: "利用目的", key: "purpose", width: 100, render: (r) => r.purpose || "—" },
  { title: "档号", key: "DH", width: 160, render: (r) => h("span", { class: "font-mono text-[12px]" }, r.DH || "—") },
  { title: "题名", key: "TM", minWidth: 180, ellipsis: { tooltip: true } },
];

function exportDetail() {
  const HEAD = ["序号", "利用日期", "利用人", "利用方式", "利用目的", "档号", "题名"];
  const esc = (v: string) => `"${v.replace(/"/g, '""')}"`;
  const lines = [HEAD.map(esc).join(",")];
  detailRows.value.forEach((r, i) => lines.push([
    String(i + 1), fmt(r.used_at), r.applicant_name, USE_TYPE_LABEL[r.use_type] ?? r.use_type, r.purpose || "", r.DH || "", r.TM,
  ].map(esc).join(",")));
  const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `利用明细_${detailPeriod.value}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
  message.success("已导出");
}

onMounted(async () => {
  const cats = (await CategoryAPI.list()).data;
  categoryMap.value = Object.fromEntries(cats.map((c: ArchiveCategory) => [c.id, `${c.code} - ${c.name}`]));
  await load();
});
</script>
