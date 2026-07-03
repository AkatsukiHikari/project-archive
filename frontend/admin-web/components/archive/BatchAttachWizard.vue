<template>
  <NModal
    :show="show"
    preset="card"
    title="挂接数字化成果"
    style="width: 920px; max-width: 96vw"
    :mask-closable="false"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <NTabs v-model:value="tab" type="line">
      <NTabPane name="new" tab="批量挂接">
        <AttachBatchPanel ref="panel" class="pt-2" @done="onDone" />
      </NTabPane>

      <NTabPane name="history" tab="挂接历史">
        <div class="flex flex-col gap-3 pt-2">
          <div class="flex items-center gap-3">
            <NButton size="small" tertiary @click="loadBatches">
              <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
              刷新
            </NButton>
            <span class="text-[12px]" style="color:var(--semi-color-text-3)">
              每次批量挂接自动留痕，点击批次查看逐文件报表
            </span>
          </div>
          <ProTable :columns="batchColumns" :data="batches" :loading="batchesLoading" :page-size="0" size="small" max-height="320" />
          <div class="flex justify-end">
            <NPagination
              v-model:page="batchPage"
              :page-size="BATCH_PAGE_SIZE"
              :item-count="batchTotal"
              size="small"
              @update:page="loadBatches"
            />
          </div>
        </div>
      </NTabPane>
    </NTabs>

    <!-- 批次明细报表 -->
    <NModal
      v-model:show="showDetail"
      preset="card"
      :title="`挂接批次 ${detail?.batch_no ?? ''} 明细报表`"
      style="width: 860px; max-width: 95vw"
    >
      <div v-if="detail" class="flex flex-col gap-3">
        <div class="flex items-center gap-4 text-[13px]" style="color:var(--semi-color-text-1)">
          <span>共 {{ detail.total }} 个文件</span>
          <span style="color:oklch(var(--su))">成功 {{ detail.attached }}</span>
          <span style="color:oklch(0.6 0.18 80)">跳过 {{ detail.skipped }}</span>
          <span style="color:oklch(var(--er))">无匹配 {{ detail.not_found }}</span>
          <span style="color:var(--semi-color-text-3)">{{ detail.create_time?.slice(0, 19).replace("T", " ") }}</span>
          <div class="flex-1" />
          <NButton size="tiny" tertiary @click="exportDetailCsv">
            <template #icon><Icon name="heroicons:arrow-down-tray" class="w-3.5 h-3.5" /></template>
            导出明细 CSV
          </NButton>
        </div>
        <ProTable :columns="detailColumns" :data="detail.rows ?? []" :page-size="0" size="small" max-height="380" />
      </div>
    </NModal>
  </NModal>
</template>

<script setup lang="tsx">
import { h, ref, watch } from "vue";
import { NButton, NModal, NPagination, NTabPane, NTabs, NTag } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { ProTable } from "@/components/ui";
import AttachBatchPanel from "./AttachBatchPanel.vue";
import { OrganizeAPI } from "@/api/repository";
import type { AttachBatchRecord, AttachMatchRow } from "@/api/repository";

const props = defineProps<{ show: boolean }>();
const emit = defineEmits<{ "update:show": [boolean]; done: [] }>();

const BATCH_PAGE_SIZE = 10;
const tab = ref("new");
const panel = ref<InstanceType<typeof AttachBatchPanel> | null>(null);

const batches = ref<AttachBatchRecord[]>([]);
const batchesLoading = ref(false);
const batchPage = ref(1);
const batchTotal = ref(0);
const showDetail = ref(false);
const detail = ref<AttachBatchRecord | null>(null);

watch(() => props.show, (v) => {
  if (v) {
    tab.value = "new";
    panel.value?.resetAll();
    loadBatches();
  }
});

function onDone() {
  emit("done");
  loadBatches();
}

async function loadBatches() {
  batchesLoading.value = true;
  try {
    const res = await OrganizeAPI.listAttachBatches({
      skip: (batchPage.value - 1) * BATCH_PAGE_SIZE,
      limit: BATCH_PAGE_SIZE,
    });
    if (res.code === 0) {
      batches.value = res.data.items;
      batchTotal.value = res.data.total;
    }
  } finally {
    batchesLoading.value = false;
  }
}

async function openDetail(id: string) {
  const res = await OrganizeAPI.getAttachBatch(id);
  if (res.code === 0) {
    detail.value = res.data;
    showDetail.value = true;
  }
}

const RESULT_LABEL: Record<string, string> = {
  attached: "已挂接", skipped: "已跳过", not_found: "无此档号",
};

function exportDetailCsv() {
  const d = detail.value;
  if (!d) return;
  const esc = (v: unknown) => `"${String(v ?? "").replace(/"/g, '""')}"`;
  const lines = [
    ["文件名", "档号", "匹配档案", "库", "结果", "说明"].map(esc).join(","),
    ...(d.rows ?? []).map((r) =>
      [
        r.filename, r.DH,
        r.TM ?? "",
        r.source === "formal" ? "正式库" : r.source === "staging" ? "暂存库" : "",
        RESULT_LABEL[r.status] ?? r.status,
        r.reason ?? "",
      ].map(esc).join(","),
    ),
  ];
  const blob = new Blob(["﻿" + lines.join("\n")], { type: "text/csv;charset=utf-8" });
  const a = document.createElement("a");
  a.href = URL.createObjectURL(blob);
  a.download = `挂接批次_${d.batch_no}.csv`;
  a.click();
  URL.revokeObjectURL(a.href);
}

const batchColumns: DataTableColumns<AttachBatchRecord> = [
  { title: "批次号", key: "batch_no", width: 150 },
  {
    title: "状态", key: "status", width: 80,
    render: (r) => h(NTag, { size: "tiny", round: true, bordered: false, type: r.status === "running" ? "info" : "success" },
      { default: () => (r.status === "running" ? "进行中" : "已完结") }),
  },
  { title: "时间", key: "create_time", width: 160, render: (r) => r.create_time?.slice(0, 19).replace("T", " ") ?? "—" },
  { title: "文件数", key: "total", width: 75 },
  {
    title: "成功", key: "attached", width: 70,
    render: (r) => h("span", { style: "color:oklch(var(--su));font-weight:600" }, String(r.attached)),
  },
  { title: "跳过", key: "skipped", width: 70 },
  {
    title: "无匹配", key: "not_found", width: 75,
    render: (r) => (r.not_found
      ? h("span", { style: "color:oklch(var(--er));font-weight:600" }, String(r.not_found))
      : "0"),
  },
  {
    title: "覆盖模式", key: "overwrite", width: 85,
    render: (r) => h(NTag, { size: "tiny", bordered: false, type: r.overwrite ? "warning" : "default" },
      { default: () => (r.overwrite ? "覆盖" : "跳过已有") }),
  },
  {
    title: "操作", key: "actions", width: 100,
    render: (r) => h(NButton, { size: "tiny", tertiary: true, onClick: () => openDetail(r.id) },
      { default: () => "查看报表" }),
  },
];

const STATUS_TAG: Record<string, { label: string; type: "success" | "warning" | "error" | "default" }> = {
  attached: { label: "已挂接", type: "success" },
  skipped: { label: "已跳过", type: "warning" },
  not_found: { label: "无此档号", type: "error" },
};

const detailColumns: DataTableColumns<AttachMatchRow> = [
  { title: "文件名", key: "filename", minWidth: 200, ellipsis: { tooltip: true } },
  { title: "档号", key: "DH", width: 190, ellipsis: { tooltip: true } },
  { title: "匹配档案", key: "TM", minWidth: 150, ellipsis: { tooltip: true }, render: (r) => r.TM ?? "—" },
  {
    title: "结果", key: "status", width: 95,
    render: (r) => {
      const meta = STATUS_TAG[r.status] ?? { label: r.status, type: "default" as const };
      return h(NTag, { size: "small", type: meta.type, round: true, bordered: false }, { default: () => meta.label });
    },
  },
  { title: "说明", key: "reason", width: 140, render: (r) => r.reason ?? "—" },
];
</script>
