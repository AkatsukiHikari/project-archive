<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="收集台账"
      description="按年度 × 移交单位汇总应交 / 已交 / 在途，逾期欠交自动催交"
      icon="heroicons:book-open"
    />

    <!-- 工具栏 -->
    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <NInputNumber
        v-model:value="year"
        placeholder="全部年度"
        :show-button="false"
        clearable
        style="width: 140px"
        @update:value="load"
      />
      <NButton tertiary @click="load">
        <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
        刷新
      </NButton>
    </div>

    <!-- KPI 看板 -->
    <div class="grid grid-cols-2 lg:grid-cols-5 gap-4">
      <StatCard label="应交（件）" :value="summary?.total_planned ?? 0" icon="heroicons:inbox-stack" tone="slate" />
      <StatCard label="已交（件）" :value="summary?.total_accepted ?? 0" icon="heroicons:check-circle" tone="green" />
      <StatCard label="在途（件）" :value="summary?.total_submitted ?? 0" icon="heroicons:truck" tone="blue" />
      <StatCard label="整体完成率" :value="`${summary?.overall_completion_rate ?? 0}%`" icon="heroicons:chart-pie" tone="violet" />
      <StatCard label="逾期单位" :value="summary?.overdue_units ?? 0" icon="heroicons:bell-alert" :tone="(summary?.overdue_units ?? 0) > 0 ? 'red' : 'slate'" />
    </div>

    <!-- 催交明细 -->
    <div class="pro-card p-5 flex flex-col gap-3">
      <div class="flex items-center justify-between">
        <p class="text-sm font-medium">催交看板</p>
        <NTag v-if="overdueRows.length" type="error" size="small" round>
          {{ overdueRows.length }} 个单位逾期欠交
        </NTag>
      </div>
      <ProTable :columns="columns" :data="summary?.rows ?? []" :loading="loading" :page-size="15" size="small" />
    </div>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted, h } from "vue";
import { NInputNumber, NButton, NTag, NProgress } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { TransferAPI } from "@/api/collection";
import type { LedgerSummary, LedgerRow } from "@/api/collection";

definePageMeta({ layout: "archive", middleware: "auth" });

const TONES: Record<string, string> = {
  slate: "text-slate-600 bg-slate-50",
  green: "text-green-600 bg-green-50",
  blue: "text-blue-600 bg-blue-50",
  violet: "text-violet-600 bg-violet-50",
  red: "text-red-600 bg-red-50",
};

const StatCard = (props: { label: string; value: string | number; icon: string; tone: string }) =>
  h("div", { class: "pro-card p-4 flex items-center gap-3" }, [
    h("div", { class: `w-10 h-10 rounded-lg flex items-center justify-center ${TONES[props.tone] ?? TONES.slate}` },
      [h(resolveIcon, { name: props.icon, class: "w-5 h-5" })]),
    h("div", { class: "flex flex-col" }, [
      h("span", { class: "text-xl font-bold tabular-nums" }, String(props.value)),
      h("span", { class: "text-xs text-gray-500" }, props.label),
    ]),
  ]);

// Nuxt 全局 <Icon> 组件，render 函数中通过 resolveComponent 获取
const resolveIcon = resolveComponent("Icon");

const loading = ref(false);
const summary = ref<LedgerSummary | null>(null);
const year = ref<number | null>(null);

const overdueRows = computed(() => (summary.value?.rows ?? []).filter((r) => r.overdue));

async function load() {
  loading.value = true;
  try {
    summary.value = (await TransferAPI.ledger(year.value ?? undefined)).data;
  } finally {
    loading.value = false;
  }
}

const columns: DataTableColumns<LedgerRow> = [
  { title: "年度", key: "year", width: 70 },
  {
    title: "移交单位", key: "source_unit", minWidth: 140,
    render: (row) =>
      h("div", { class: "flex items-center gap-2" }, [
        h("span", row.source_unit),
        row.overdue ? h(NTag, { type: "error", size: "tiny", round: true }, () => "逾期") : null,
      ]),
  },
  { title: "应交", key: "planned_count", width: 80 },
  { title: "已交", key: "accepted_count", width: 80, render: (row) => h("span", { class: "text-green-600 font-medium" }, String(row.accepted_count)) },
  { title: "在途", key: "submitted_count", width: 80, render: (row) => h("span", { class: "text-blue-600" }, String(row.submitted_count)) },
  {
    title: "完成率", key: "completion_rate", width: 180,
    render: (row) =>
      h("div", { class: "flex items-center gap-2" }, [
        h(NProgress, {
          type: "line", percentage: Math.min(row.completion_rate, 100), height: 6,
          showIndicator: false, style: "width: 90px",
          status: row.completion_rate >= 100 ? "success" : row.overdue ? "error" : "default",
        }),
        h("span", { class: "text-xs tabular-nums text-gray-500" }, `${row.completion_rate}%`),
      ]),
  },
  { title: "移交单数", key: "batch_total", width: 90 },
  {
    title: "应交截止", key: "due_date", width: 110,
    render: (row) =>
      row.due_date
        ? h("span", { class: row.overdue ? "text-red-500" : "text-gray-500" }, row.due_date)
        : h("span", { class: "text-gray-300" }, "—"),
  },
];

onMounted(load);
</script>
