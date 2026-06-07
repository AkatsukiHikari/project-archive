<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="归档移交"
      description="各部门编制移交清单、移交至档案室，支持四性预检自检"
      icon="heroicons:arrow-down-tray"
    />

    <!-- 工具栏 -->
    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <NSelect
        v-model:value="filterStatus"
        :options="statusFilterOptions"
        placeholder="全部状态"
        clearable
        style="width: 160px"
        @update:value="loadBatches"
      />
      <NInputNumber
        v-model:value="filterYear"
        placeholder="年度"
        :show-button="false"
        clearable
        style="width: 120px"
        @update:value="loadBatches"
      />
      <NButton tertiary @click="loadBatches">
        <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
        刷新
      </NButton>
      <div class="flex-1" />
      <NButton type="primary" @click="openCreate">
        <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
        新建移交单
      </NButton>
    </div>

    <!-- 移交单列表 -->
    <div class="pro-card p-5">
      <ProTable :columns="columns" :data="batches" :loading="loading" :page-size="10" size="small" />
    </div>

    <!-- 新建移交单 -->
    <NModal
      v-model:show="showCreate"
      preset="card"
      title="新建移交单"
      style="width: 980px; max-width: 95vw"
      :mask-closable="false"
    >
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-3 gap-4">
          <LabeledField label="移交单位" required>
            <NInput v-model:value="form.source_unit" placeholder="如：办公室" />
          </LabeledField>
          <LabeledField label="移交经办人" required>
            <NInput v-model:value="form.handover_person" placeholder="经办人姓名" />
          </LabeledField>
          <LabeledField label="档案年度" required>
            <NInputNumber v-model:value="form.year" :show-button="false" class="w-full" />
          </LabeledField>
          <LabeledField label="全宗" required>
            <NSelect v-model:value="form.fonds_id" :options="fondsOptions" placeholder="选择全宗" @update:value="onFondsChange" />
          </LabeledField>
          <LabeledField label="门类" required>
            <NSelect v-model:value="form.category_id" :options="categoryOptions" placeholder="选择门类" />
          </LabeledField>
          <LabeledField label="目标目录">
            <NSelect v-model:value="form.catalog_id" :options="catalogOptions" placeholder="可接收时再定" :disabled="!form.fonds_id" clearable />
          </LabeledField>
        </div>

        <!-- 明细编辑 -->
        <div class="flex items-center justify-between">
          <p class="text-sm font-medium">移交清单（{{ draftEntries.length }} 条）</p>
          <div class="flex gap-2">
            <NButton size="small" @click="addEntry">
              <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
              添加条目
            </NButton>
            <NButton size="small" tertiary @click="showBulk = !showBulk">批量粘贴</NButton>
          </div>
        </div>

        <NInput
          v-if="showBulk"
          v-model:value="bulkText"
          type="textarea"
          :rows="4"
          placeholder="每行一条，制表符/逗号分隔：题名 责任者 年度 文件日期 页数 密级 保管期限"
          @blur="applyBulk"
        />

        <div class="border rounded-lg overflow-hidden">
          <div class="grid grid-cols-[2fr_1.2fr_0.8fr_1fr_0.6fr_1fr_1fr_40px] gap-px bg-gray-100 text-xs font-medium text-gray-500">
            <div class="bg-gray-50 px-2 py-1.5">题名 *</div>
            <div class="bg-gray-50 px-2 py-1.5">责任者</div>
            <div class="bg-gray-50 px-2 py-1.5">年度</div>
            <div class="bg-gray-50 px-2 py-1.5">文件日期</div>
            <div class="bg-gray-50 px-2 py-1.5">页数</div>
            <div class="bg-gray-50 px-2 py-1.5">密级</div>
            <div class="bg-gray-50 px-2 py-1.5">保管期限</div>
            <div class="bg-gray-50 px-2 py-1.5" />
          </div>
          <div class="max-h-72 overflow-y-auto">
            <div
              v-for="(e, i) in draftEntries"
              :key="i"
              class="grid grid-cols-[2fr_1.2fr_0.8fr_1fr_0.6fr_1fr_1fr_40px] gap-px bg-gray-100"
            >
              <NInput v-model:value="e.TM" size="small" placeholder="题名" />
              <NInput v-model:value="e.RZZ" size="small" />
              <NInputNumber v-model:value="e.ND" size="small" :show-button="false" />
              <NInput v-model:value="e.WJRQ" size="small" placeholder="2024-01-01" />
              <NInputNumber v-model:value="e.YS" size="small" :show-button="false" />
              <NSelect v-model:value="e.MJ" size="small" :options="mjOptions" />
              <NSelect v-model:value="e.BGQX" size="small" :options="bgqxOptions" />
              <button class="bg-white flex items-center justify-center text-gray-400 hover:text-red-500" @click="draftEntries.splice(i, 1)">
                <Icon name="heroicons:trash" class="w-4 h-4" />
              </button>
            </div>
          </div>
          <div v-if="!draftEntries.length" class="py-8 text-center text-sm text-gray-400 bg-white">
            暂无条目，点击「添加条目」或「批量粘贴」录入
          </div>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end gap-3">
          <NButton @click="showCreate = false">取消</NButton>
          <NButton type="primary" :loading="saving" @click="submitCreate">创建移交单</NButton>
        </div>
      </template>
    </NModal>

    <!-- 移交单详情 -->
    <NModal
      v-model:show="showDetail"
      preset="card"
      :title="`移交单 ${detail?.transfer_no ?? ''}`"
      style="width: 900px; max-width: 95vw"
    >
      <div v-if="detail" class="flex flex-col gap-4">
        <div class="flex items-center gap-3">
          <TransferStatusTag :status="detail.status" />
          <span class="text-sm text-gray-500">{{ detail.source_unit }} · {{ detail.year }} 年度 · {{ detail.expected_count }} 件</span>
        </div>

        <div v-if="detail.return_reason" class="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">
          退回原因：{{ detail.return_reason }}
        </div>

        <ProTable :columns="entryColumns" :data="detail.entries" :page-size="0" size="small" max-height="280" />

        <div v-if="previewResult" class="border-t pt-4">
          <PrecheckPanel :result="previewResult" />
        </div>
      </div>

      <template #footer>
        <div class="flex justify-between">
          <NButton tertiary :loading="previewing" @click="runPreview">
            <template #icon><Icon name="heroicons:shield-check" class="w-4 h-4" /></template>
            四性预检自检
          </NButton>
          <NButton
            v-if="detail && ['draft', 'returned'].includes(detail.status)"
            type="primary"
            :loading="submitting"
            @click="submitTransfer"
          >
            <template #icon><Icon name="heroicons:paper-airplane" class="w-4 h-4" /></template>
            提交移交
          </NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, reactive, computed, onMounted, h } from "vue";
import {
  NSelect, NInput, NInputNumber, NButton, NModal, NTag, useMessage, useDialog,
} from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { PrecheckPanel, TransferStatusTag } from "@/components/archive";
import { FondsAPI, CatalogAPI, CategoryAPI } from "@/api/repository";
import type { Fonds, Catalog, ArchiveCategory } from "@/api/repository";
import { TransferAPI } from "@/api/collection";
import type {
  TransferBatch, TransferBatchDetail, TransferEntryIn, TransferEntryOut,
  TransferStatus, PrecheckResponse,
} from "@/api/collection";

type SlotsCtx = { slots: { default?: () => unknown } };
type TagType = "default" | "info" | "success" | "warning" | "error";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();

const mjOptions = [
  { label: "公开", value: "public" }, { label: "内部", value: "internal" },
  { label: "秘密", value: "confidential" }, { label: "机密", value: "secret" },
];
const bgqxOptions = [
  { label: "永久", value: "permanent" }, { label: "长期", value: "long" }, { label: "短期", value: "short" },
];
const statusFilterOptions = [
  { label: "草稿", value: "draft" }, { label: "待接收", value: "submitted" },
  { label: "已签收", value: "received" }, { label: "已接收入库", value: "accepted" },
  { label: "已退回", value: "returned" },
];

// 简易标签字段容器
const LabeledField = (props: { label: string; required?: boolean }, { slots }: SlotsCtx) =>
  h("div", { class: "flex flex-col gap-1" }, [
    h("span", { class: "text-sm font-medium" }, [
      props.label,
      props.required ? h("span", { class: "text-red-500 ml-0.5" }, "*") : null,
    ]),
    slots.default?.(),
  ]);

// ── 选项数据 ──────────────────────────────────────────────────────
const fondsList = ref<Fonds[]>([]);
const catalogList = ref<Catalog[]>([]);
const categoryList = ref<ArchiveCategory[]>([]);
const fondsOptions = computed(() => fondsList.value.map((f) => ({ label: `${f.fonds_code} - ${f.name}`, value: f.id })));
const catalogOptions = computed(() => catalogList.value.map((c) => ({ label: `${c.catalog_no} ${c.name}`, value: c.id })));
const categoryOptions = computed(() => categoryList.value.map((c) => ({ label: `${c.code} - ${c.name}`, value: c.id })));

async function onFondsChange(id: string | null) {
  form.catalog_id = null;
  catalogList.value = id ? (await CatalogAPI.list(id)).data : [];
}

// ── 列表 ──────────────────────────────────────────────────────────
const loading = ref(false);
const batches = ref<TransferBatch[]>([]);
const filterStatus = ref<string | null>(null);
const filterYear = ref<number | null>(null);

async function loadBatches() {
  loading.value = true;
  try {
    const res = await TransferAPI.listBatches({
      status: (filterStatus.value as TransferStatus) ?? undefined,
      year: filterYear.value ?? undefined,
    });
    batches.value = res.data;
  } finally {
    loading.value = false;
  }
}

const columns: DataTableColumns<TransferBatch> = [
  { title: "移交单号", key: "transfer_no", width: 150 },
  { title: "移交单位", key: "source_unit", width: 140 },
  { title: "年度", key: "year", width: 70 },
  { title: "件数", key: "expected_count", width: 70 },
  {
    title: "状态", key: "status", width: 120,
    render: (row) => h(TransferStatusTag, { status: row.status }),
  },
  {
    title: "四性总分", key: "precheck_score", width: 90,
    render: (row) =>
      row.precheck_score == null
        ? h("span", { class: "text-gray-300" }, "—")
        : h("span", {
            class: row.precheck_score >= 60 ? "text-green-600 font-medium" : "text-red-600 font-medium",
          }, row.precheck_score.toFixed(0)),
  },
  {
    title: "操作", key: "actions", width: 90,
    render: (row) => h(NButton, { size: "small", tertiary: true, onClick: () => openDetail(row.id) }, () => "详情"),
  },
];

// ── 创建 ──────────────────────────────────────────────────────────
const showCreate = ref(false);
const saving = ref(false);
const showBulk = ref(false);
const bulkText = ref("");
const form = reactive({
  source_unit: "", handover_person: "", year: new Date().getFullYear(),
  fonds_id: null as string | null, category_id: null as string | null, catalog_id: null as string | null,
});
const draftEntries = ref<TransferEntryIn[]>([]);

function newEntry(): TransferEntryIn {
  return { TM: "", RZZ: null, ND: form.year, WJRQ: null, YS: null, MJ: "public", BGQX: "permanent" };
}
function addEntry() { draftEntries.value.push(newEntry()); }

function applyBulk() {
  const lines = bulkText.value.split("\n").map((l) => l.trim()).filter(Boolean);
  for (const line of lines) {
    const c = line.split(/[\t,]/).map((s) => s.trim());
    if (!c[0]) continue;
    draftEntries.value.push({
      TM: c[0], RZZ: c[1] || null,
      ND: c[2] ? Number(c[2]) : form.year,
      WJRQ: c[3] || null, YS: c[4] ? Number(c[4]) : null,
      MJ: c[5] || "public", BGQX: c[6] || "permanent",
    });
  }
  bulkText.value = "";
  showBulk.value = false;
}

function openCreate() {
  form.source_unit = ""; form.handover_person = ""; form.year = new Date().getFullYear();
  form.fonds_id = null; form.category_id = null; form.catalog_id = null;
  draftEntries.value = [newEntry()];
  showCreate.value = true;
}

async function submitCreate() {
  if (!form.source_unit || !form.handover_person || !form.fonds_id || !form.category_id) {
    message.warning("请填写移交单位、经办人、全宗与门类");
    return;
  }
  const entries = draftEntries.value.filter((e) => (e.TM ?? "").trim());
  if (!entries.length) {
    message.warning("请至少录入一条有效条目（题名必填）");
    return;
  }
  saving.value = true;
  try {
    await TransferAPI.createBatch({
      source_unit: form.source_unit, handover_person: form.handover_person, year: form.year,
      fonds_id: form.fonds_id, category_id: form.category_id, catalog_id: form.catalog_id, entries,
    });
    message.success("移交单已创建");
    showCreate.value = false;
    await loadBatches();
  } finally {
    saving.value = false;
  }
}

// ── 详情 ──────────────────────────────────────────────────────────
const showDetail = ref(false);
const detail = ref<TransferBatchDetail | null>(null);
const previewResult = ref<PrecheckResponse | null>(null);
const previewing = ref(false);
const submitting = ref(false);

const entryColumns: DataTableColumns<TransferEntryOut> = [
  { title: "#", key: "row_no", width: 50 },
  { title: "题名", key: "TM", ellipsis: { tooltip: true } },
  { title: "责任者", key: "RZZ", width: 120 },
  { title: "年度", key: "ND", width: 70 },
  { title: "文件日期", key: "WJRQ", width: 110 },
  {
    title: "预检", key: "precheck_status", width: 90,
    render: (row) => {
      const map: Record<string, [string, TagType]> = {
        ok: ["合格", "success"], warning: ["警告", "warning"], error: ["错误", "error"], pending: ["待检", "default"],
      };
      const [label, type] = map[row.precheck_status] ?? ["待检", "default"];
      return h(NTag, { size: "small", type }, () => label);
    },
  },
];

async function openDetail(id: string) {
  previewResult.value = null;
  detail.value = (await TransferAPI.getBatch(id)).data;
  showDetail.value = true;
}

async function runPreview() {
  if (!detail.value) return;
  previewing.value = true;
  try {
    previewResult.value = (await TransferAPI.previewPrecheck(detail.value.id)).data;
  } finally {
    previewing.value = false;
  }
}

function submitTransfer() {
  if (!detail.value) return;
  dialog.info({
    title: "提交移交",
    content: "提交后移交单进入档案室接收队列，期间将无法编辑明细，确认提交？",
    positiveText: "确认提交",
    negativeText: "取消",
    onPositiveClick: async () => {
      submitting.value = true;
      try {
        await TransferAPI.submitBatch(detail.value!.id);
        message.success("已提交移交");
        showDetail.value = false;
        await loadBatches();
      } finally {
        submitting.value = false;
      }
    },
  });
}

onMounted(async () => {
  fondsList.value = (await FondsAPI.list()).data;
  categoryList.value = (await CategoryAPI.list()).data;
  await loadBatches();
});
</script>
