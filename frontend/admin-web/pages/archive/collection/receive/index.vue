<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="接收登记"
      description="档案室签收移交单，四性预检通过后接收入库，不合格可退回"
      icon="heroicons:clipboard-document-check"
    />

    <!-- 工具栏 -->
    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <NSelect
        v-model:value="filterStatus"
        :options="queueOptions"
        style="width: 180px"
        @update:value="loadQueue"
      />
      <NButton tertiary @click="loadQueue">
        <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
        刷新
      </NButton>
      <div class="flex-1" />
      <span class="text-sm text-gray-500">待处理 {{ batches.length }} 单</span>
    </div>

    <!-- 接收队列 -->
    <div class="pro-card p-5">
      <ProTable :columns="columns" :data="batches" :loading="loading" :page-size="10" size="small" />
    </div>

    <!-- 接收处理抽屉 -->
    <NDrawer v-model:show="showPanel" :width="560" placement="right">
      <NDrawerContent :title="`接收处理 · ${current?.transfer_no ?? ''}`" closable>
        <div v-if="current" class="flex flex-col gap-4">
          <div class="grid grid-cols-2 gap-3 text-sm">
            <InfoItem label="移交单位" :value="current.source_unit" />
            <InfoItem label="经办人" :value="current.handover_person" />
            <InfoItem label="档案年度" :value="String(current.year)" />
            <InfoItem label="申报件数" :value="String(current.expected_count)" />
          </div>

          <div class="flex items-center gap-2">
            <TransferStatusTag :status="current.status" />
            <NButton size="small" type="primary" :loading="prechecking" @click="runPrecheck">
              <template #icon><Icon name="heroicons:shield-check" class="w-4 h-4" /></template>
              {{ result ? "重新预检" : "执行四性预检" }}
            </NButton>
          </div>

          <PrecheckPanel :result="result" />

          <!-- 接收决策 -->
          <div v-if="canDecide" class="border-t pt-4 flex flex-col gap-3">
            <LabeledField label="目标目录" :required="!current.catalog_id">
              <NSelect v-model:value="acceptCatalog" :options="catalogOptions" placeholder="选择入库目录" clearable />
            </LabeledField>

            <div
              v-if="result && !result.passed"
              class="rounded-lg border border-amber-200 bg-amber-50 p-3 text-sm text-amber-700 flex items-start gap-2"
            >
              <Icon name="heroicons:exclamation-triangle" class="w-5 h-5 shrink-0 mt-0.5" />
              <div>
                <p>四性预检未通过闸门。建议退回整改；如确需接收，请勾选强制接收。</p>
                <NCheckbox v-model:checked="forceAccept" class="mt-2">强制接收（留痕审计）</NCheckbox>
              </div>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="flex justify-between w-full">
            <NButton type="error" ghost :disabled="!canDecide" @click="openReturn">
              <template #icon><Icon name="heroicons:arrow-uturn-left" class="w-4 h-4" /></template>
              退回
            </NButton>
            <NButton type="primary" :disabled="!canAccept" :loading="accepting" @click="doAccept">
              <template #icon><Icon name="heroicons:check-badge" class="w-4 h-4" /></template>
              接收入库
            </NButton>
          </div>
        </template>
      </NDrawerContent>
    </NDrawer>

    <!-- 退回原因 -->
    <NModal v-model:show="showReturn" preset="dialog" title="退回移交单" type="warning">
      <NInput v-model:value="returnReason" type="textarea" :rows="3" placeholder="请填写退回原因（移交单位可见）" />
      <template #action>
        <NButton @click="showReturn = false">取消</NButton>
        <NButton type="error" :loading="returning" @click="doReturn">确认退回</NButton>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted, h } from "vue";
import {
  NSelect, NButton, NDrawer, NDrawerContent, NModal, NInput, NCheckbox, useMessage,
} from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { PrecheckPanel, TransferStatusTag } from "@/components/archive";
import { CatalogAPI } from "@/api/repository";
import type { Catalog } from "@/api/repository";
import { TransferAPI } from "@/api/collection";
import type { TransferBatch, TransferStatus, PrecheckResponse } from "@/api/collection";

type SlotsCtx = { slots: { default?: () => unknown } };

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();

const queueOptions = [
  { label: "待接收 + 已签收", value: "all" },
  { label: "待接收（submitted）", value: "submitted" },
  { label: "已签收（received）", value: "received" },
];

const InfoItem = (props: { label: string; value: string }) =>
  h("div", { class: "flex flex-col" }, [
    h("span", { class: "text-xs text-gray-400" }, props.label),
    h("span", { class: "font-medium" }, props.value),
  ]);
const LabeledField = (props: { label: string; required?: boolean }, { slots }: SlotsCtx) =>
  h("div", { class: "flex flex-col gap-1" }, [
    h("span", { class: "text-sm font-medium" }, [
      props.label,
      props.required ? h("span", { class: "text-red-500 ml-0.5" }, "*") : null,
    ]),
    slots.default?.(),
  ]);

// ── 队列 ──────────────────────────────────────────────────────────
const loading = ref(false);
const batches = ref<TransferBatch[]>([]);
const filterStatus = ref("all");

async function loadQueue() {
  loading.value = true;
  try {
    if (filterStatus.value === "all") {
      const [a, b] = await Promise.all([
        TransferAPI.listBatches({ status: "submitted" }),
        TransferAPI.listBatches({ status: "received" }),
      ]);
      batches.value = [...a.data, ...b.data];
    } else {
      batches.value = (await TransferAPI.listBatches({ status: filterStatus.value as TransferStatus })).data;
    }
  } finally {
    loading.value = false;
  }
}

const columns: DataTableColumns<TransferBatch> = [
  { title: "移交单号", key: "transfer_no", width: 150 },
  { title: "移交单位", key: "source_unit", width: 140 },
  { title: "年度", key: "year", width: 70 },
  { title: "件数", key: "expected_count", width: 70 },
  { title: "状态", key: "status", width: 110, render: (row) => h(TransferStatusTag, { status: row.status }) },
  {
    title: "操作", key: "actions", width: 90,
    render: (row) => h(NButton, { size: "small", type: "primary", tertiary: true, onClick: () => openPanel(row) }, () => "处理"),
  },
];

// ── 处理面板 ──────────────────────────────────────────────────────
const showPanel = ref(false);
const current = ref<TransferBatch | null>(null);
const result = ref<PrecheckResponse | null>(null);
const prechecking = ref(false);
const accepting = ref(false);
const forceAccept = ref(false);
const acceptCatalog = ref<string | null>(null);
const catalogList = ref<Catalog[]>([]);
const catalogOptions = computed(() => catalogList.value.map((c) => ({ label: `${c.catalog_no} ${c.name}`, value: c.id })));

const canDecide = computed(() => current.value?.status === "received");
const canAccept = computed(() => {
  if (!canDecide.value) return false;
  if (!(acceptCatalog.value || current.value?.catalog_id)) return false;
  if (result.value && !result.value.passed && !forceAccept.value) return false;
  return true;
});

async function openPanel(row: TransferBatch) {
  current.value = row;
  result.value = row.precheck_detail ? { ...row.precheck_detail, entries: [] } : null;
  forceAccept.value = false;
  acceptCatalog.value = row.catalog_id ?? null;
  catalogList.value = row.fonds_id ? (await CatalogAPI.list(row.fonds_id)).data : [];
  showPanel.value = true;
}

async function runPrecheck() {
  if (!current.value) return;
  prechecking.value = true;
  try {
    result.value = (await TransferAPI.receivePrecheck(current.value.id)).data;
    current.value.status = "received";
    current.value.precheck_passed = result.value.passed;
    current.value.precheck_score = result.value.score;
    await loadQueue();
  } finally {
    prechecking.value = false;
  }
}

async function doAccept() {
  if (!current.value) return;
  accepting.value = true;
  try {
    await TransferAPI.accept(current.value.id, {
      catalog_id: acceptCatalog.value ?? undefined,
      force: forceAccept.value,
    });
    message.success("已接收入库，明细已转入暂存库待著录审核");
    showPanel.value = false;
    await loadQueue();
  } finally {
    accepting.value = false;
  }
}

// ── 退回 ──────────────────────────────────────────────────────────
const showReturn = ref(false);
const returnReason = ref("");
const returning = ref(false);

function openReturn() {
  returnReason.value = "";
  showReturn.value = true;
}

async function doReturn() {
  if (!current.value) return;
  if (!returnReason.value.trim()) {
    message.warning("请填写退回原因");
    return;
  }
  returning.value = true;
  try {
    await TransferAPI.returnBatch(current.value.id, returnReason.value.trim());
    message.success("已退回移交单位");
    showReturn.value = false;
    showPanel.value = false;
    await loadQueue();
  } finally {
    returning.value = false;
  }
}

onMounted(loadQueue);
</script>
