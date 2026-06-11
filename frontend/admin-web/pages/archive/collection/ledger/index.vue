<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="收集台账"
      description="移交接收明细登记表 · 逐条登记，可筛选 / 导出 / 打印备查"
      icon="heroicons:book-open"
    />

    <!-- 视图切换 + 筛选 -->
    <div class="pro-card p-4 flex flex-wrap items-end gap-3">
      <NTabs v-model:value="view" type="segment" size="small" style="width: 240px">
        <NTab name="register">登记表</NTab>
        <NTab name="overview">催交概览</NTab>
      </NTabs>
      <template v-if="view === 'register'">
        <div class="flex flex-col gap-1">
          <span class="text-xs text-gray-500">状态</span>
          <NSelect v-model:value="filters.status" :options="statusOptions" placeholder="全部" clearable style="width: 150px" />
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-xs text-gray-500">年度</span>
          <NInputNumber v-model:value="filters.year" :show-button="false" placeholder="年度" clearable style="width: 110px" />
        </div>
        <NButton type="primary" :loading="loadingReg" @click="loadRegister">
          <template #icon><Icon name="heroicons:magnifying-glass" class="w-4 h-4" /></template>
          查询
        </NButton>
        <NButton tertiary @click="resetFilters">重置</NButton>
        <div class="flex-1" />
        <NButton tertiary :disabled="!batches.length" @click="exportCsv">
          <template #icon><Icon name="heroicons:arrow-down-tray" class="w-4 h-4" /></template>
          导出 CSV
        </NButton>
        <NButton tertiary :disabled="!batches.length" @click="printLedger">
          <template #icon><Icon name="heroicons:printer" class="w-4 h-4" /></template>
          打印
        </NButton>
      </template>
      <template v-else>
        <NInputNumber v-model:value="ovYear" placeholder="全部年度" :show-button="false" clearable style="width: 140px" @update:value="loadOverview" />
        <NButton tertiary @click="loadOverview">
          <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
          刷新
        </NButton>
      </template>
    </div>

    <!-- 登记表视图 -->
    <div v-if="view === 'register'" class="pro-card p-5 flex flex-col gap-2">
      <div class="flex items-center justify-between">
        <p class="text-sm font-medium">移交接收明细</p>
        <span class="text-sm text-gray-500">合计 <strong>{{ batches.length }}</strong> 单 · {{ totalItems }} 件</span>
      </div>
      <ProTable :columns="columns" :data="batches" :loading="loadingReg" :page-size="20" size="small" />
    </div>

    <!-- 催交概览视图（统计，非台账） -->
    <template v-else>
      <div class="grid grid-cols-2 lg:grid-cols-5 gap-4">
        <StatCard label="应交（件）" :value="summary?.total_planned ?? 0" icon="heroicons:inbox-stack" tone="slate" />
        <StatCard label="已交（件）" :value="summary?.total_accepted ?? 0" icon="heroicons:check-circle" tone="green" />
        <StatCard label="在途（件）" :value="summary?.total_submitted ?? 0" icon="heroicons:truck" tone="blue" />
        <StatCard label="整体完成率" :value="`${summary?.overall_completion_rate ?? 0}%`" icon="heroicons:chart-pie" tone="violet" />
        <StatCard label="逾期单位" :value="summary?.overdue_units ?? 0" icon="heroicons:bell-alert" :tone="(summary?.overdue_units ?? 0) > 0 ? 'red' : 'slate'" />
      </div>
      <div class="pro-card p-5 flex flex-col gap-3">
        <p class="text-sm font-medium">催交看板</p>
        <ProTable :columns="ovColumns" :data="summary?.rows ?? []" :loading="loadingOv" :page-size="15" size="small" />
      </div>
    </template>
  </div>
</template>

<script setup lang="tsx">
import { ref, reactive, computed, onMounted, h } from "vue";
import { NSelect, NInputNumber, NButton, NTabs, NTab, NProgress, NTag, useMessage } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { TransferStatusTag } from "@/components/archive";
import { TransferAPI } from "@/api/collection";
import type { LedgerSummary, LedgerRow, TransferBatch, TransferStatus } from "@/api/collection";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const view = ref<"register" | "overview">("register");

const statusOptions = [
  { label: "草稿", value: "draft" },
  { label: "待接收", value: "submitted" },
  { label: "已签收", value: "received" },
  { label: "已接收入库", value: "accepted" },
  { label: "已退回", value: "returned" },
];
const STATUS_LABEL: Record<string, string> = {
  draft: "草稿", submitted: "待接收", received: "已签收", accepted: "已接收入库", returned: "已退回",
};

const fmtDate = (s?: string | null): string => (s ? s.slice(0, 10) : "—");

// ── 登记表 ────────────────────────────────────────────────────────
const loadingReg = ref(false);
const batches = ref<TransferBatch[]>([]);
const filters = reactive<{ status: string | null; year: number | null }>({ status: null, year: null });
const totalItems = computed(() => batches.value.reduce((s, b) => s + (b.expected_count || 0), 0));

async function loadRegister() {
  loadingReg.value = true;
  try {
    const res = await TransferAPI.listBatches({
      status: (filters.status as TransferStatus) ?? undefined,
      year: filters.year ?? undefined,
    });
    batches.value = res.data;
  } finally {
    loadingReg.value = false;
  }
}
function resetFilters() { filters.status = null; filters.year = null; loadRegister(); }

const columns: DataTableColumns<TransferBatch> = [
  { title: "序号", key: "_idx", width: 60, render: (_r, i) => i + 1 },
  { title: "移交单号", key: "transfer_no", width: 150, render: (r) => h("span", { class: "font-mono text-[12px]" }, r.transfer_no) },
  { title: "移交单位", key: "source_unit", minWidth: 140 },
  { title: "经办人", key: "handover_person", width: 100 },
  { title: "年度", key: "year", width: 70 },
  { title: "移交日期", key: "handover_date", width: 110, render: (r) => fmtDate(r.handover_date) },
  { title: "接收日期", key: "accepted_at", width: 110, render: (r) => fmtDate(r.accepted_at) },
  { title: "件数", key: "expected_count", width: 70 },
  { title: "状态", key: "status", width: 120, render: (r) => h(TransferStatusTag, { status: r.status }) },
];

const HEADERS = ["序号", "移交单号", "移交单位", "经办人", "年度", "移交日期", "接收日期", "件数", "状态"];
function rowToCells(r: TransferBatch, i: number): string[] {
  return [
    String(i + 1), r.transfer_no, r.source_unit, r.handover_person, String(r.year),
    fmtDate(r.handover_date), fmtDate(r.accepted_at), String(r.expected_count),
    STATUS_LABEL[r.status] ?? r.status,
  ];
}

function exportCsv() {
  const esc = (v: string) => `"${v.replace(/"/g, '""')}"`;
  const lines = [HEADERS.map(esc).join(",")];
  batches.value.forEach((r, i) => lines.push(rowToCells(r, i).map(esc).join(",")));
  lines.push(esc(`合计 ${batches.value.length} 单 ${totalItems.value} 件`));
  const blob = new Blob(["﻿" + lines.join("\r\n")], { type: "text/csv;charset=utf-8;" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `收集台账_${new Date().toISOString().slice(0, 10)}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
  message.success("已导出 CSV");
}

function printLedger() {
  const w = window.open("", "_blank");
  if (!w) { message.warning("打印窗口被拦截，请允许弹窗"); return; }
  const esc = (v: string) => v.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const cond: string[] = [];
  if (filters.status) cond.push(`状态：${STATUS_LABEL[filters.status]}`);
  if (filters.year) cond.push(`年度：${filters.year}`);
  const body = batches.value.map((r, i) => "<tr>" + rowToCells(r, i).map((c) => `<td>${esc(c)}</td>`).join("") + "</tr>").join("");
  w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>收集台账</title>
    <style>
      body{font-family:"Microsoft YaHei",sans-serif;padding:24px;color:#111}
      h1{font-size:18px;text-align:center;margin:0 0 6px}
      .meta{font-size:12px;color:#555;text-align:center;margin-bottom:12px}
      table{width:100%;border-collapse:collapse;font-size:12px}
      th,td{border:1px solid #999;padding:4px 6px;text-align:left}
      th{background:#f0f0f0}
      tfoot td{font-weight:bold}
    </style></head><body>
    <h1>收集台账（移交接收明细登记表）</h1>
    <div class="meta">${cond.length ? "筛选：" + esc(cond.join("　")) + " ｜ " : ""}合计 ${batches.value.length} 单 ${totalItems.value} 件 ｜ 打印时间：${new Date().toLocaleString("zh-CN")}</div>
    <table><thead><tr>${HEADERS.map((h2) => `<th>${h2}</th>`).join("")}</tr></thead>
    <tbody>${body}</tbody>
    <tfoot><tr><td colspan="${HEADERS.length}">合计 ${batches.value.length} 单 ${totalItems.value} 件</td></tr></tfoot></table>
    </body></html>`);
  w.document.close();
  w.focus();
  setTimeout(() => w.print(), 300);
}

// ── 催交概览 ──────────────────────────────────────────────────────
const TONES: Record<string, string> = {
  slate: "text-slate-600 bg-slate-50", green: "text-green-600 bg-green-50",
  blue: "text-blue-600 bg-blue-50", violet: "text-violet-600 bg-violet-50", red: "text-red-600 bg-red-50",
};
const resolveIcon = resolveComponent("Icon");
const StatCard = (props: { label: string; value: string | number; icon: string; tone: string }) =>
  h("div", { class: "pro-card p-4 flex items-center gap-3" }, [
    h("div", { class: `w-10 h-10 rounded-lg flex items-center justify-center ${TONES[props.tone] ?? TONES.slate}` },
      [h(resolveIcon, { name: props.icon, class: "w-5 h-5" })]),
    h("div", { class: "flex flex-col" }, [
      h("span", { class: "text-xl font-bold tabular-nums" }, String(props.value)),
      h("span", { class: "text-xs text-gray-500" }, props.label),
    ]),
  ]);

const loadingOv = ref(false);
const summary = ref<LedgerSummary | null>(null);
const ovYear = ref<number | null>(null);

async function loadOverview() {
  loadingOv.value = true;
  try {
    summary.value = (await TransferAPI.ledger(ovYear.value ?? undefined)).data;
  } finally {
    loadingOv.value = false;
  }
}

const ovColumns: DataTableColumns<LedgerRow> = [
  { title: "年度", key: "year", width: 70 },
  {
    title: "移交单位", key: "source_unit", minWidth: 140,
    render: (row) => h("div", { class: "flex items-center gap-2" }, [
      h("span", row.source_unit),
      row.overdue ? h(NTag, { type: "error", size: "tiny", round: true }, () => "逾期") : null,
    ]),
  },
  { title: "应交", key: "planned_count", width: 80 },
  { title: "已交", key: "accepted_count", width: 80, render: (row) => h("span", { class: "text-green-600 font-medium" }, String(row.accepted_count)) },
  { title: "在途", key: "submitted_count", width: 80, render: (row) => h("span", { class: "text-blue-600" }, String(row.submitted_count)) },
  {
    title: "完成率", key: "completion_rate", width: 180,
    render: (row) => h("div", { class: "flex items-center gap-2" }, [
      h(NProgress, { type: "line", percentage: Math.min(row.completion_rate, 100), height: 6, showIndicator: false, style: "width: 90px", status: row.completion_rate >= 100 ? "success" : row.overdue ? "error" : "default" }),
      h("span", { class: "text-xs tabular-nums text-gray-500" }, `${row.completion_rate}%`),
    ]),
  },
  {
    title: "应交截止", key: "due_date", width: 110,
    render: (row) => row.due_date
      ? h("span", { class: row.overdue ? "text-red-500" : "text-gray-500" }, row.due_date)
      : h("span", { class: "text-gray-300" }, "—"),
  },
];

onMounted(async () => {
  await loadRegister();
  await loadOverview();
});
</script>
