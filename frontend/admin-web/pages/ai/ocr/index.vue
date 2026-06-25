<template>
  <div class="flex flex-col gap-4">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2.5">
        <div
          class="w-9 h-9 rounded-xl flex items-center justify-center"
          style="background: linear-gradient(135deg, oklch(var(--p)) 0%, oklch(var(--p)/0.72) 100%); box-shadow: 0 2px 10px oklch(var(--p)/0.35)"
        >
          <Icon name="heroicons:document-magnifying-glass" class="w-5 h-5 text-white" />
        </div>
        <h1 class="text-base font-semibold" style="color: var(--semi-color-text-0)">OCR 任务</h1>
      </div>
      <div class="flex items-center gap-2">
        <NSelect v-model:value="filterStatus" :options="statusOptions" placeholder="全部状态" clearable size="small" style="width: 130px" @update:value="load" />
        <NButton size="small" :loading="batching" @click="doBatch">
          <template #icon><Icon name="heroicons:bolt" class="w-4 h-4" /></template>
          批量识别未 OCR 档案
        </NButton>
        <NButton text size="small" :loading="loading" @click="load">
          <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
          刷新
        </NButton>
      </div>
    </div>

    <div v-if="running > 0" class="flex items-center gap-2 text-xs px-3 py-2 rounded-lg" style="background: oklch(var(--p)/0.06); color: var(--semi-color-text-2)">
      <NSpin size="small" />
      有 {{ running }} 个任务进行中，每 3 秒自动刷新…
    </div>

    <div class="pro-card p-2">
      <NDataTable :columns="columns" :data="jobs" :loading="loading" :pagination="pagination" :row-key="(r: OcrJob) => r.id" size="small" />
    </div>
  </div>
</template>

<script setup lang="tsx">
import { computed, h, onMounted, onUnmounted, reactive, ref } from "vue";
import { NButton, NDataTable, NSelect, NSpin, NTag, useMessage } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AiAdminAPI, type OcrJob } from "@/api/ai";

definePageMeta({
  layout: "archive",
  middleware: "auth",
  breadcrumb: [
    { name: "AI 档案助手", path: "/ai" },
    { name: "OCR 任务", path: "/ai/ocr" },
  ],
});
useHead({ title: "OCR 任务" });

const message = useMessage();
const jobs = ref<OcrJob[]>([]);
const loading = ref(false);
const batching = ref(false);
const filterStatus = ref<string | null>(null);
let timer: ReturnType<typeof setInterval> | null = null;

const statusOptions = [
  { label: "排队中", value: "pending" },
  { label: "识别中", value: "running" },
  { label: "成功", value: "succeeded" },
  { label: "失败", value: "failed" },
];

const STATUS_META: Record<string, { label: string; type: "default" | "info" | "success" | "error" | "warning" }> = {
  pending: { label: "排队中", type: "default" },
  running: { label: "识别中", type: "info" },
  succeeded: { label: "成功", type: "success" },
  failed: { label: "失败", type: "error" },
};

const running = computed(() => jobs.value.filter((j) => j.status === "pending" || j.status === "running").length);

const pagination = reactive({ pageSize: 20 });

const columns: DataTableColumns<OcrJob> = [
  { title: "档号", key: "archive_dh", width: 180, render: (r) => h("span", { class: "font-mono text-xs" }, r.archive_dh || "—") },
  { title: "题名", key: "archive_tm", ellipsis: { tooltip: true }, render: (r) => r.archive_tm || "—" },
  {
    title: "状态", key: "status", width: 90,
    render: (r) => {
      const m = STATUS_META[r.status] ?? { label: r.status, type: "default" as const };
      return h(NTag, { type: m.type, size: "small", round: true }, { default: () => m.label });
    },
  },
  {
    title: "结果", key: "result", width: 160, ellipsis: { tooltip: true },
    render: (r) =>
      r.status === "succeeded"
        ? h("span", { style: "color: var(--semi-color-text-2)" }, `识别 ${r.chars ?? 0} 字`)
        : r.status === "failed"
          ? h("span", { style: "color: #dc2626" }, r.error || "失败")
          : h("span", { style: "color: var(--semi-color-text-3)" }, "—"),
  },
  { title: "触发时间", key: "create_time", width: 150, render: (r) => fmt(r.create_time) },
];

function fmt(s?: string): string {
  if (!s) return "—";
  return new Date(s).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" });
}

async function load() {
  loading.value = true;
  try {
    const res = await AiAdminAPI.ocrJobs({ status: filterStatus.value ?? undefined, limit: 100 });
    jobs.value = res.data.items;
  } finally {
    loading.value = false;
  }
}

async function doBatch() {
  batching.value = true;
  try {
    const res = await AiAdminAPI.ocrBatch();
    message.success(`已投递 ${res.data.queued} 个 OCR 任务`);
    load();
  } finally {
    batching.value = false;
  }
}

onMounted(() => {
  load();
  timer = setInterval(() => {
    if (running.value > 0) load();
  }, 3000);
});
onUnmounted(() => {
  if (timer) clearInterval(timer);
});
</script>
