<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader title="四性检测" description="电子档案真实性 / 完整性 / 可用性 / 安全性检测，按方案逐项检测、AI 与人工结合" icon="heroicons:shield-check" />

    <NTabs v-model:value="tab" type="line" animated>
      <!-- ── 检测记录 ── -->
      <NTabPane name="runs" tab="检测批次">
        <div class="flex flex-col gap-4">
          <div class="pro-card p-4 flex items-center gap-3">
            <NButton tertiary @click="loadBatches">刷新</NButton>
            <div class="flex-1" />
            <NButton type="primary" @click="openRun">
              <template #icon><Icon name="heroicons:play" class="w-4 h-4" /></template>
              发起检测
            </NButton>
          </div>
          <div class="pro-card p-5">
            <ProTable :columns="batchColumns" :data="batches" :loading="loadingBatches" :page-size="15" size="small" />
          </div>
        </div>
      </NTabPane>

      <!-- ── 检测方案 ── -->
      <NTabPane name="schemes" tab="检测方案">
        <div class="flex flex-col gap-4">
          <div class="pro-card p-4 flex items-center gap-3">
            <NButton tertiary @click="loadSchemes">刷新</NButton>
            <div class="flex-1" />
            <NButton type="primary" @click="openScheme()">
              <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
              新建方案
            </NButton>
          </div>
          <div class="pro-card p-5">
            <ProTable :columns="schemeColumns" :data="schemes" :loading="loadingSchemes" :page-size="15" size="small" />
          </div>
        </div>
      </NTabPane>

      <!-- ── 检测项目录 ── -->
      <NTabPane name="catalog" tab="检测项目录">
        <div class="pro-card p-5 flex flex-col gap-4">
          <div v-for="dim in DIMS" :key="dim" class="flex flex-col gap-2">
            <div class="text-sm font-semibold flex items-center gap-2" style="color:var(--semi-color-text-0)">
              <span class="w-1.5 h-4 rounded" :style="{ background: DIM_COLOR[dim] }" />{{ DIM_LABEL[dim] }}
            </div>
            <div v-for="it in itemsByDim(dim)" :key="it.code" class="flex items-center gap-2 text-[13px] pl-3.5">
              <NTag size="tiny" :type="EXEC_TONE[it.exec_type]" :bordered="false">{{ EXEC_LABEL[it.exec_type] }}</NTag>
              <span style="color:var(--semi-color-text-0)">{{ it.name }}</span>
              <NTag v-if="it.default_blocking" size="tiny" type="warning" :bordered="false">必检</NTag>
              <span class="text-[11px]" style="color:var(--semi-color-text-3)">{{ it.standard_ref }}</span>
            </div>
          </div>
        </div>
      </NTabPane>
    </NTabs>

    <!-- 发起检测 -->
    <NModal v-model:show="showRun" preset="card" title="发起四性检测" style="width: 560px; max-width: 95vw">
      <div class="flex flex-col gap-3">
        <NRadioGroup v-model:value="runMode" size="small">
          <NRadioButton value="single">单件检测</NRadioButton>
          <NRadioButton value="batch">按目录批量检测</NRadioButton>
        </NRadioGroup>

        <template v-if="runMode === 'single'">
          <div class="flex flex-col gap-1">
            <span class="text-sm" style="color:var(--semi-color-text-2)">检测对象（搜索档号 / 题名）</span>
            <NSelect v-model:value="runForm.archive_id" filterable remote :options="archiveOptions" :loading="searching" placeholder="输入关键词搜索档案" @search="searchArchive" />
          </div>
        </template>
        <template v-else>
          <div class="grid grid-cols-2 gap-3">
            <div class="flex flex-col gap-1">
              <span class="text-sm" style="color:var(--semi-color-text-2)">全宗</span>
              <NSelect v-model:value="batchForm.fonds_id" :options="fondsOptions" placeholder="选择全宗" clearable filterable @update:value="onBatchFonds" />
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-sm" style="color:var(--semi-color-text-2)">目录</span>
              <NSelect v-model:value="batchForm.catalog_id" :options="catalogOptions" placeholder="全部目录" clearable filterable :disabled="!batchForm.fonds_id" />
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-sm" style="color:var(--semi-color-text-2)">门类</span>
              <NSelect v-model:value="batchForm.category_id" :options="categoryOptions" placeholder="全部门类" clearable filterable />
            </div>
            <div class="flex flex-col gap-1">
              <span class="text-sm" style="color:var(--semi-color-text-2)">年度</span>
              <NInputNumber v-model:value="batchForm.ND" :show-button="false" placeholder="全部年度" class="w-full" />
            </div>
          </div>
          <p class="text-[12px]" style="color:var(--semi-color-text-3)">将对所选范围内的全部档案逐件检测（至少选一个条件）。</p>
        </template>

        <div class="flex flex-col gap-1">
          <span class="text-sm" style="color:var(--semi-color-text-2)">检测方案</span>
          <NSelect v-model:value="runForm.scheme_id" :options="schemeOptions" placeholder="默认方案" clearable />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-2">
          <NButton @click="showRun = false">取消</NButton>
          <NButton v-if="runMode === 'single'" type="primary" :loading="running" :disabled="!runForm.archive_id" @click="confirmRun">开始检测</NButton>
          <NButton v-else type="primary" :loading="running" :disabled="!hasBatchScope" @click="confirmBatch">开始批量检测</NButton>
        </div>
      </template>
    </NModal>

    <!-- 批次报告抽屉 -->
    <NDrawer v-model:show="showReport" :width="780" placement="right">
      <NDrawerContent title="四性检测批次报告" closable>
        <BatchReportPanel :batch-id="reportBatchId" @open-run="openRunReport" />
      </NDrawerContent>
    </NDrawer>
    <!-- 单件报告抽屉（批次内下钻） -->
    <NDrawer v-model:show="showRunReport" :width="640" placement="right">
      <NDrawerContent title="单件检测报告" closable>
        <DetectionReportPanel :run-id="runReportId" @changed="loadBatches" />
      </NDrawerContent>
    </NDrawer>

    <!-- 方案编辑 -->
    <NModal v-model:show="showScheme" preset="card" :title="schemeEditId ? '编辑检测方案' : '新建检测方案'" style="width: 720px; max-width: 95vw">
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="flex flex-col gap-1"><span class="text-sm font-medium">方案名称 <span class="text-red-500">*</span></span><NInput v-model:value="schemeForm.name" placeholder="方案名称" /></div>
          <div class="flex flex-col gap-1"><span class="text-sm font-medium">说明</span><NInput v-model:value="schemeForm.description" placeholder="说明" /></div>
        </div>
        <div class="flex flex-col gap-3 max-h-[50vh] overflow-y-auto pr-1">
          <div v-for="dim in DIMS" :key="dim" class="flex flex-col gap-1.5">
            <div class="text-[13px] font-semibold flex items-center gap-2"><span class="w-1.5 h-4 rounded" :style="{ background: DIM_COLOR[dim] }" />{{ DIM_LABEL[dim] }}</div>
            <div v-for="it in itemsByDim(dim)" :key="it.code" class="flex items-center gap-2 pl-3.5 py-1 rounded" style="background:var(--semi-color-fill-0)">
              <NCheckbox :checked="selected.has(it.code)" @update:checked="(c) => toggleItem(it.code, c)" />
              <NTag size="tiny" :type="EXEC_TONE[it.exec_type]" :bordered="false">{{ EXEC_LABEL[it.exec_type] }}</NTag>
              <span class="text-[13px] flex-1" style="color:var(--semi-color-text-0)">{{ it.name }}</span>
              <span class="text-[11px]" style="color:var(--semi-color-text-3)">{{ it.standard_ref }}</span>
              <NCheckbox :checked="blocking.has(it.code)" :disabled="!selected.has(it.code)" @update:checked="(c) => toggleBlocking(it.code, c)">必检</NCheckbox>
            </div>
          </div>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <NButton @click="showScheme = false">取消</NButton>
          <NButton type="primary" :loading="savingScheme" @click="saveScheme">{{ schemeEditId ? '保存' : '创建' }}</NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, reactive, computed, onMounted, h } from "vue";
import { NTabs, NTabPane, NButton, NModal, NSelect, NInput, NInputNumber, NTag, NCheckbox, NRadioGroup, NRadioButton, NDrawer, NDrawerContent, useMessage, useDialog } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { DetectionReportPanel, BatchReportPanel } from "@/components/archive";
import { PreservationAPI } from "@/api/preservation";
import type { CheckItem, Scheme, Batch, Dimension } from "@/api/preservation";
import { ArchiveAPI, FondsAPI, CategoryAPI, CatalogAPI } from "@/api/repository";
import type { Fonds, ArchiveCategory, Catalog } from "@/api/repository";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();
const tab = ref("runs");

const DIMS: Dimension[] = ["authenticity", "integrity", "usability", "safety"];
const DIM_LABEL: Record<string, string> = { authenticity: "真实性", integrity: "完整性", usability: "可用性", safety: "安全性" };
const DIM_COLOR: Record<string, string> = { authenticity: "#2563eb", integrity: "#059669", usability: "#d97706", safety: "#dc2626" };
const EXEC_LABEL: Record<string, string> = { rule: "规则", ai: "AI", manual: "人工" };
const EXEC_TONE: Record<string, "default" | "info" | "warning"> = { rule: "default", ai: "info", manual: "warning" };
const CONCLUSION_LABEL: Record<string, string> = { pass: "合格", warn: "基本合格", fail: "不合格", pending: "待复核" };
const CONCLUSION_TONE: Record<string, "success" | "warning" | "error" | "info"> = { pass: "success", warn: "warning", fail: "error", pending: "info" };

const fmt = (s?: string | null) => (s ? s.replace("T", " ").slice(0, 16) : "—");

// ── 检测项目录 ────────────────────────────────────────────────────
const checkItems = ref<CheckItem[]>([]);
const itemsByDim = (d: string) => checkItems.value.filter((x) => x.dimension === d);

// ── 检测批次 ──────────────────────────────────────────────────────
const loadingBatches = ref(false);
const batches = ref<Batch[]>([]);
async function loadBatches() {
  loadingBatches.value = true;
  try { batches.value = (await PreservationAPI.batches()).data; } finally { loadingBatches.value = false; }
}
const scopeText = (b: Batch) => (b.scope_type === "single" ? `单件 · ${b.scope_label || "—"}` : b.scope_label || "—");
const batchColumns: DataTableColumns<Batch> = [
  { title: "批次号", key: "batch_no", width: 150, render: (b) => h("span", { class: "font-mono text-[12px]" }, b.batch_no) },
  { title: "检测范围", key: "scope_label", minWidth: 240, ellipsis: { tooltip: true }, render: scopeText },
  { title: "方案", key: "scheme_name", width: 170, ellipsis: { tooltip: true } },
  { title: "件数", key: "total", width: 70, render: (b) => `${b.total} 件` },
  { title: "结论", key: "conclusion", width: 110, render: (b) => h(NTag, { size: "small", type: CONCLUSION_TONE[b.conclusion], round: true }, () => CONCLUSION_LABEL[b.conclusion]) },
  { title: "合格/不合格/待复核", key: "stat", width: 150, render: (b) => h("span", {}, [h("span", { class: "text-green-600" }, String(b.passed)), " / ", h("span", { class: "text-red-600" }, String(b.failed)), " / ", h("span", { class: "text-blue-600" }, String(b.pending))]) },
  { title: "均分", key: "avg_score", width: 70, render: (b) => h("span", { class: "tabular-nums font-medium" }, String(b.avg_score)) },
  { title: "检测时间", key: "finished_at", width: 140, render: (b) => fmt(b.finished_at) },
  { title: "操作", key: "actions", width: 90, fixed: "right", render: (b) => h(NButton, { size: "small", type: "primary", tertiary: true, onClick: () => openReport(b) }, () => "报告") },
];

// ── 发起检测 ──────────────────────────────────────────────────────
const showRun = ref(false);
const running = ref(false);
const searching = ref(false);
const runMode = ref<"single" | "batch">("single");
const archiveOptions = ref<{ label: string; value: string }[]>([]);
const runForm = reactive<{ archive_id: string | null; scheme_id: string | null }>({ archive_id: null, scheme_id: null });

// 批量范围
const fondsList = ref<Fonds[]>([]);
const categoryList = ref<ArchiveCategory[]>([]);
const catalogList = ref<Catalog[]>([]);
const fondsOptions = computed(() => fondsList.value.map((f) => ({ label: `${f.fonds_code} - ${f.name}`, value: f.id })));
const categoryOptions = computed(() => categoryList.value.map((c) => ({ label: `${c.code} - ${c.name}`, value: c.id })));
const catalogOptions = computed(() => catalogList.value.map((c) => ({ label: `${c.catalog_no} ${c.name}`, value: c.id })));
const batchForm = reactive<{ fonds_id: string | null; catalog_id: string | null; category_id: string | null; ND: number | null }>({ fonds_id: null, catalog_id: null, category_id: null, ND: null });
const hasBatchScope = computed(() => !!(batchForm.fonds_id || batchForm.catalog_id || batchForm.category_id || batchForm.ND));

function openRun() {
  runMode.value = "single";
  runForm.archive_id = null; runForm.scheme_id = null; archiveOptions.value = [];
  Object.assign(batchForm, { fonds_id: null, catalog_id: null, category_id: null, ND: null });
  catalogList.value = [];
  showRun.value = true;
}
async function searchArchive(q: string) {
  if (!q.trim()) return;
  searching.value = true;
  try {
    const res = await ArchiveAPI.list({ keyword: q.trim(), page_size: 20 });
    archiveOptions.value = res.data.items.map((a) => ({ label: `${a.DH || ""} ${a.TM}`.trim(), value: a.id }));
  } finally { searching.value = false; }
}
async function onBatchFonds(id: string | null) {
  batchForm.catalog_id = null;
  catalogList.value = id ? (await CatalogAPI.list(id)).data : [];
}
async function confirmRun() {
  if (!runForm.archive_id) return;
  running.value = true;
  try {
    const res = await PreservationAPI.runDetection({ archive_id: runForm.archive_id, scheme_id: runForm.scheme_id ?? undefined });
    const d = res.data;
    message.success(`检测完成：${CONCLUSION_LABEL[d.conclusion]}（均分 ${d.avg_score}）`);
    showRun.value = false;
    await loadBatches();
    openReport(d);
  } finally { running.value = false; }
}
async function confirmBatch() {
  if (!hasBatchScope.value) return;
  running.value = true;
  try {
    const res = await PreservationAPI.runBatch({
      scheme_id: runForm.scheme_id ?? undefined,
      fonds_id: batchForm.fonds_id ?? undefined, catalog_id: batchForm.catalog_id ?? undefined,
      category_id: batchForm.category_id ?? undefined, ND: batchForm.ND ?? undefined,
    });
    const d = res.data;
    message.success(`批量检测 ${d.total} 件：合格 ${d.passed} · 基本合格 ${d.warned} · 不合格 ${d.failed} · 待复核 ${d.pending}`);
    showRun.value = false;
    await loadBatches();
    openReport(d);
  } finally { running.value = false; }
}

// ── 报告 ──────────────────────────────────────────────────────────
const showReport = ref(false);
const reportBatchId = ref<string | null>(null);
function openReport(b: Batch) { reportBatchId.value = b.id; showReport.value = true; }
const showRunReport = ref(false);
const runReportId = ref<string | null>(null);
function openRunReport(runId: string) { runReportId.value = runId; showRunReport.value = true; }

// ── 检测方案 ──────────────────────────────────────────────────────
const loadingSchemes = ref(false);
const schemes = ref<Scheme[]>([]);
const schemeOptions = computed(() => schemes.value.map((s) => ({ label: s.name + (s.is_default ? "（默认）" : ""), value: s.id })));
async function loadSchemes() {
  loadingSchemes.value = true;
  try { schemes.value = (await PreservationAPI.schemes()).data; } finally { loadingSchemes.value = false; }
}
const schemeColumns: DataTableColumns<Scheme> = [
  { title: "方案名称", key: "name", minWidth: 180, render: (r) => h("div", { class: "flex items-center gap-2" }, [h("span", r.name), r.is_default ? h(NTag, { size: "tiny", type: "primary", round: true }, () => "默认") : null]) },
  { title: "检测项", key: "item_count", width: 80, render: (r) => `${r.item_count} 项` },
  { title: "版本", key: "version", width: 70, render: (r) => `v${r.version}` },
  { title: "说明", key: "description", minWidth: 160, ellipsis: { tooltip: true }, render: (r) => r.description || "—" },
  {
    title: "操作", key: "actions", width: 200, fixed: "right",
    render: (r) => h("div", { class: "flex gap-2" }, [
      h(NButton, { size: "small", tertiary: true, onClick: () => openScheme(r) }, () => "编辑"),
      r.is_default ? null : h(NButton, { size: "small", tertiary: true, onClick: () => setDefault(r) }, () => "设默认"),
      r.is_default ? null : h(NButton, { size: "small", tertiary: true, type: "error", onClick: () => removeScheme(r) }, () => "删除"),
    ]),
  },
];

const showScheme = ref(false);
const savingScheme = ref(false);
const schemeEditId = ref<string | null>(null);
const schemeForm = reactive({ name: "", description: "" });
const selected = ref<Set<string>>(new Set());
const blocking = ref<Set<string>>(new Set());

function toggleItem(code: string, c: boolean) {
  const s = new Set(selected.value);
  if (c) s.add(code); else { s.delete(code); const b = new Set(blocking.value); b.delete(code); blocking.value = b; }
  selected.value = s;
}
function toggleBlocking(code: string, c: boolean) {
  const b = new Set(blocking.value);
  if (c) b.add(code); else b.delete(code);
  blocking.value = b;
}

async function openScheme(r?: Scheme) {
  schemeForm.name = ""; schemeForm.description = ""; selected.value = new Set(); blocking.value = new Set();
  schemeEditId.value = r?.id ?? null;
  if (r) {
    const d = (await PreservationAPI.getScheme(r.id)).data;
    schemeForm.name = d.name; schemeForm.description = d.description || "";
    selected.value = new Set(d.items.map((i) => i.check_code));
    blocking.value = new Set(d.items.filter((i) => i.is_blocking).map((i) => i.check_code));
  } else {
    // 新建默认勾选全部 + 各项默认必检
    selected.value = new Set(checkItems.value.map((i) => i.code));
    blocking.value = new Set(checkItems.value.filter((i) => i.default_blocking).map((i) => i.code));
  }
  showScheme.value = true;
}

async function saveScheme() {
  if (!schemeForm.name.trim()) { message.warning("请填写方案名称"); return; }
  if (selected.value.size === 0) { message.warning("请至少勾选一个检测项"); return; }
  const items = checkItems.value.filter((i) => selected.value.has(i.code)).map((i, idx) => ({
    check_code: i.code, enabled: true, is_blocking: blocking.value.has(i.code), sort_order: idx,
  }));
  savingScheme.value = true;
  try {
    if (schemeEditId.value) await PreservationAPI.updateScheme(schemeEditId.value, { name: schemeForm.name, description: schemeForm.description, items });
    else await PreservationAPI.createScheme({ name: schemeForm.name, description: schemeForm.description, items });
    message.success("已保存");
    showScheme.value = false;
    await loadSchemes();
  } finally { savingScheme.value = false; }
}

async function setDefault(r: Scheme) { await PreservationAPI.setDefault(r.id); message.success("已设为默认"); await loadSchemes(); }
function removeScheme(r: Scheme) {
  dialog.warning({ title: "删除方案", content: `确认删除「${r.name}」？`, positiveText: "删除", negativeText: "取消", onPositiveClick: async () => { await PreservationAPI.deleteScheme(r.id); message.success("已删除"); await loadSchemes(); } });
}

onMounted(async () => {
  checkItems.value = (await PreservationAPI.checkItems()).data;
  const [f, c] = await Promise.all([FondsAPI.list(), CategoryAPI.list()]);
  fondsList.value = f.data;
  categoryList.value = c.data;
  await Promise.all([loadBatches(), loadSchemes()]);
});
</script>
