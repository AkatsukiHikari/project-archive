<template>
  <div class="flex flex-col gap-3 min-h-0 flex-1">
    <!-- ── 页头 ─────────────────────────────────────────── -->
    <div class="flex items-start justify-between gap-3">
      <AdminPageHeader
        title="智能校对"
        description="批量比对条目著录与原文全文，发现错录、漏录并一键整改"
        icon="heroicons:document-check"
      />
      <div class="flex items-center gap-2 shrink-0">
        <NSelect v-model:value="docSource" :options="sourceOptions" size="small" style="width: 110px" @update:value="onSourceChange" />
        <NButton size="small" tertiary @click="batchShow = true">
          <template #icon><Icon name="heroicons:clock" class="w-4 h-4" /></template>
          历史批次
        </NButton>
        <NButton type="primary" size="small" :loading="starting" :disabled="!!activeBatch" @click="confirmStart">
          <template #icon><Icon name="heroicons:play" class="w-4 h-4" /></template>
          开始校对
        </NButton>
      </div>
    </div>

    <!-- ── 运行中批次进度 ───────────────────────────────── -->
    <div v-if="activeBatch" class="pro-card px-4 py-3 flex items-center gap-4">
      <Icon name="heroicons:arrow-path" class="w-4 h-4 animate-spin shrink-0" style="color: oklch(var(--p))" />
      <div class="flex flex-col gap-1 flex-1 min-w-0">
        <div class="flex items-center gap-3 text-[13px]" style="color: var(--semi-color-text-0)">
          <span class="font-medium">正在校对：{{ activeBatch.scope_label || "全库" }}</span>
          <span class="tabular-nums" style="color: var(--semi-color-text-2)">{{ activeBatch.processed }} / {{ activeBatch.total }}</span>
          <span v-if="activeBatch.flagged" class="text-[12px]" style="color: var(--semi-color-warning)">待确认 {{ activeBatch.flagged }}</span>
          <span v-if="activeBatch.no_text" class="text-[12px]" style="color: var(--semi-color-text-3)">无原文 {{ activeBatch.no_text }}</span>
        </div>
        <NProgress
          type="line"
          :percentage="progressPct"
          :show-indicator="false"
          :height="6"
          processing
        />
      </div>
      <NButton size="tiny" tertiary type="error" @click="cancelBatch">取消</NButton>
    </div>

    <!-- ── 检索区 ───────────────────────────────────────── -->
    <div class="pro-card p-4 flex flex-col gap-3">
      <div class="flex items-stretch gap-3">
        <NInput
          v-model:value="keyword"
          placeholder="题名 / 责任者 / 档号"
          clearable
          class="flex-1"
          @keydown.enter="search"
        >
          <template #prefix><Icon name="heroicons:magnifying-glass" class="w-4 h-4" style="color: var(--semi-color-text-3)" /></template>
        </NInput>
        <NSelect v-model:value="verdictFilter" :options="verdictOptions" placeholder="全部状态" clearable style="width: 140px" @update:value="search" />
        <NButton type="primary" :loading="loading" @click="search">检索</NButton>
        <NButton tertiary @click="reset">重置</NButton>
        <NButton text type="primary" @click="advanced = !advanced">
          <Icon :name="advanced ? 'heroicons:chevron-up' : 'heroicons:adjustments-horizontal'" class="w-4 h-4 mr-1" />
          {{ advanced ? "收起" : "高级查询" }}
        </NButton>
      </div>
      <div v-show="advanced" class="grid grid-cols-2 lg:grid-cols-4 gap-x-4 gap-y-3 pt-2 border-t" style="border-color: var(--semi-color-border)">
        <Field label="题名"><NInput v-model:value="form.TM" placeholder="题名关键字" clearable /></Field>
        <Field label="责任者"><NInput v-model:value="form.RZZ" placeholder="责任者" clearable /></Field>
        <Field label="档号"><NInput v-model:value="form.DH" placeholder="档号" clearable /></Field>
        <Field label="年度">
          <div class="flex items-center gap-1">
            <NInputNumber v-model:value="form.ND_from" :show-button="false" placeholder="起" class="flex-1" />
            <span style="color: var(--semi-color-text-3)">~</span>
            <NInputNumber v-model:value="form.ND_to" :show-button="false" placeholder="止" class="flex-1" />
          </div>
        </Field>
      </div>
    </div>

    <!-- ── 目录导航 + 结果表 ────────────────────────────── -->
    <div class="flex gap-3 flex-1 min-h-0">
      <CatalogNavTree ref="navTree" :source="docSource" @select="onNavSelect" @clear="onNavClear" />

      <div class="pro-card p-4 flex-1 min-w-0 min-h-0 flex flex-col gap-3">
        <!-- 最近校对结果横幅：有待确认条目时必须一眼看到 -->
        <div
          v-if="latestBatch && !activeBatch && latestBatch.flagged > 0"
          class="flex items-center gap-2.5 px-3 py-2 rounded-lg shrink-0"
          style="background: color-mix(in srgb, var(--semi-color-danger) 8%, transparent)"
        >
          <Icon name="heroicons:exclamation-triangle" class="w-4.5 h-4.5 shrink-0" style="color: var(--semi-color-danger)" />
          <span class="text-[13px]" style="color: var(--semi-color-text-0)">
            最近校对（{{ latestBatch.scope_label || "全库" }}）发现
            <strong style="color: var(--semi-color-danger)">{{ latestBatch.flagged }}</strong>
            条档案的著录与原文不符，等待人工确认
          </span>
          <div class="flex-1" />
          <NButton size="tiny" type="error" secondary @click="filterFlagged">只看待确认</NButton>
        </div>

        <div class="flex items-center gap-3">
          <NTag v-if="navScope" size="small" type="info" round closable @close="clearNavTag">
            目录：{{ navScope.label }}
          </NTag>
          <span class="text-[13px]" style="color: var(--semi-color-text-2)">共 <strong>{{ total }}</strong> 条</span>
          <div class="flex-1" />
          <NButton text size="small" :loading="loading" @click="load">
            <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
            刷新
          </NButton>
        </div>
        <NDataTable
          :columns="columns"
          :data="rows"
          :loading="loading"
          :row-key="(r: ProofreadRecord) => r.id"
          :row-props="rowProps"
          size="small"
          class="flex-1"
          :scroll-x="1080"
        />
        <div class="flex justify-end">
          <NPagination v-model:page="page" :page-count="pageCount" :page-size="pageSize" show-quick-jumper @update:page="load" />
        </div>
      </div>
    </div>

    <!-- ── 历史批次 ─────────────────────────────────────── -->
    <NDrawer v-model:show="batchShow" :width="640" placement="right">
      <NDrawerContent title="校对批次记录" closable>
        <NDataTable :columns="batchColumns" :data="batches" :loading="batchLoading" size="small" :row-key="(b: ProofreadBatch) => b.id" />
      </NDrawerContent>
    </NDrawer>

    <!-- ── 人工确认（复用著录抽屉，但关闭自动采用：表单保持现值，AI 建议逐项手动采用） ── -->
    <AiCatalogDrawer v-model:show="drawerShow" :archive="target" :auto-adopt="false" @applied="onResolved" />
  </div>
</template>

<script setup lang="tsx">
import { computed, h, onActivated, onBeforeUnmount, onDeactivated, onMounted, reactive, ref, watch } from "vue";
import {
  NButton, NCheckbox, NDataTable, NDrawer, NDrawerContent, NInput, NInputNumber,
  NPagination, NPopover, NProgress, NSelect, NTag, useDialog, useMessage,
} from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { AiCatalogDrawer, CatalogNavTree } from "@/components/archive";
import {
  ProofreadAPI,
  type ProofreadBatch, type ProofreadDocSource, type ProofreadQuery, type ProofreadRecord,
} from "@/api/proofread";

definePageMeta({
  layout: "archive",
  middleware: "auth",
  breadcrumb: [
    { name: "AI 档案助手", path: "/ai" },
    { name: "智能校对", path: "/ai/proofread" },
  ],
});
useHead({ title: "智能校对" });

const router = useRouter();
const message = useMessage();
const dialog = useDialog();

// ── 检索条件 ──────────────────────────────────────────────────────────────────
const docSource = ref<ProofreadDocSource>("all");
const sourceOptions = [
  { label: "全部库", value: "all" },
  { label: "正式库", value: "formal" },
  { label: "暂存库", value: "staging" },
];
const keyword = ref("");
const advanced = ref(false);
const form = reactive<{ TM?: string; RZZ?: string; DH?: string; ND_from?: number | null; ND_to?: number | null }>({});
interface NavScope {
  category_id?: string;
  fonds_id?: string;
  ND_from?: number;
  ND_to?: number;
  label: string;
}
const navScope = ref<NavScope | null>(null);
const navTree = ref<{ clear: () => void } | null>(null);
const verdictFilter = ref<string | null>(null);
const verdictOptions = [
  { label: "需要确认（与原文不符）", value: "flagged" },
  { label: "还未校对", value: "none" },
  { label: "与原文一致", value: "consistent" },
  { label: "已确认", value: "resolved" },
  { label: "原文识别不出文字", value: "no_text" },
  { label: "校对失败", value: "failed" },
  { label: "无原文", value: "no_pdf" },
];

function filterFlagged() {
  verdictFilter.value = "flagged";
  page.value = 1;
  load();
}

const Field = (props: { label: string }, { slots }: { slots: { default?: () => unknown } }) =>
  h("div", { class: "flex flex-col gap-1" }, [
    h("span", { class: "text-xs", style: "color:var(--semi-color-text-3)" }, props.label),
    slots.default?.(),
  ]);

function buildQuery(): ProofreadQuery {
  const clean = (v?: string) => (v && v.trim() ? v.trim() : undefined);
  return {
    keyword: clean(keyword.value),
    TM: clean(form.TM),
    RZZ: clean(form.RZZ),
    DH: clean(form.DH),
    category_id: navScope.value?.category_id,
    fonds_id: navScope.value?.fonds_id,
    ND_from: navScope.value?.ND_from ?? form.ND_from ?? undefined,
    ND_to: navScope.value?.ND_to ?? form.ND_to ?? undefined,
    page: page.value,
    page_size: pageSize.value,
  };
}

function scopeLabel(): string {
  const parts: string[] = [];
  parts.push(navScope.value?.label || (docSource.value === "all" ? "全库" : docSource.value === "formal" ? "正式库" : "暂存库"));
  if (keyword.value.trim()) parts.push(`关键字「${keyword.value.trim()}」`);
  if (form.TM?.trim()) parts.push(`题名「${form.TM.trim()}」`);
  if (form.RZZ?.trim()) parts.push(`责任者「${form.RZZ.trim()}」`);
  if (form.DH?.trim()) parts.push(`档号「${form.DH.trim()}」`);
  if (!navScope.value && (form.ND_from || form.ND_to)) parts.push(`${form.ND_from ?? ""}~${form.ND_to ?? ""}年`);
  return parts.join(" · ");
}

function onNavSelect(scope: NavScope) {
  navScope.value = scope;
  page.value = 1;
  load();
}
function onNavClear() {
  navScope.value = null;
  page.value = 1;
  load();
}
function clearNavTag() {
  navTree.value?.clear();
}
function onSourceChange() {
  navScope.value = null;
  page.value = 1;
  load();
}

// ── 结果表（服务端分页） ──────────────────────────────────────────────────────
const loading = ref(false);
const rows = ref<ProofreadRecord[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)));

async function load() {
  loading.value = true;
  try {
    const res = await ProofreadAPI.records(docSource.value, buildQuery(), verdictFilter.value ?? undefined);
    if (res.code !== 0) return message.error(res.message);
    rows.value = res.data.items;
    total.value = res.data.total;
  } finally {
    loading.value = false;
  }
}
function search() { page.value = 1; load(); }
function reset() {
  keyword.value = "";
  Object.assign(form, { TM: "", RZZ: "", DH: "", ND_from: undefined, ND_to: undefined });
  verdictFilter.value = null;
  navTree.value?.clear();
}

const KIND_LABEL: Record<string, string> = { fill: "漏录", correct: "疑错" };

// 校对结果：这一列只回答一件事——"这条需不需要你来确认"
function renderVerdict(r: ProofreadRecord) {
  if (r.verdict === "flagged" && r.issues?.length) {
    const maxConf = Math.max(...r.issues.map((it) => it.confidence));
    const tag = h("div", { class: "flex items-center gap-1.5 cursor-pointer" }, [
      h(NTag, { size: "small", type: "error", bordered: false, class: "font-medium" },
        { default: () => `请确认：${r.issue_count} 处与原文不符` }),
      h("span", { class: "text-[11px] tabular-nums font-medium", style: "color:var(--semi-color-danger)" }, `${maxConf}%`),
    ]);
    // 悬停展开：每个字段 现值 → 原文值 · 置信度
    return h(
      NPopover,
      { trigger: "hover", placement: "left", style: "max-width: 440px" },
      {
        trigger: () => tag,
        default: () =>
          h("div", { class: "flex flex-col gap-1.5 py-1" }, [
            ...r.issues!.map((it) =>
              h("div", { class: "text-[12px] leading-relaxed" }, [
                h(NTag, { size: "tiny", type: it.kind === "correct" ? "error" : "warning", bordered: false, class: "mr-1.5" },
                  { default: () => KIND_LABEL[it.kind] ?? it.kind }),
                h("span", { class: "font-medium", style: "color:var(--semi-color-text-0)" }, it.label),
                h("span", { style: "color:var(--semi-color-text-2)" }, `：${it.current || "（空）"} → `),
                h("span", { class: "font-medium", style: "color:var(--semi-color-success)" }, it.suggested || "—"),
                h("span", { class: "text-[11px] ml-1 tabular-nums", style: "color:var(--semi-color-text-3)" }, `置信度 ${it.confidence}%`),
              ]),
            ),
            r.checked_at
              ? h("div", { class: "text-[11px] pt-1 border-t", style: "color:var(--semi-color-text-3);border-color:var(--semi-color-border)" },
                  `分析时间 ${r.checked_at.slice(0, 16).replace("T", " ")}`)
              : null,
          ]),
      },
    );
  }
  const SUBTLE: Record<string, { label: string; color: string }> = {
    consistent: { label: "与原文一致，无需处理", color: "var(--semi-color-success)" },
    resolved: { label: "已确认", color: "var(--semi-color-info)" },
    pending: { label: "校对中…", color: "var(--semi-color-info)" },
    no_text: { label: "原文识别不出文字", color: "var(--semi-color-warning)" },
    failed: { label: "校对失败", color: "var(--semi-color-danger)" },
    none: { label: "还未校对", color: "var(--semi-color-text-3)" },
    no_pdf: { label: "无原文，无法校对", color: "var(--semi-color-text-3)" },
  };
  const m = SUBTLE[r.verdict] ?? SUBTLE.none;
  return h("span", { class: "text-[12px]", style: `color:${m.color}` }, m.label);
}

// 待确认行整行淡红底，一眼可辨
function rowProps(r: ProofreadRecord) {
  if (r.verdict !== "flagged") return {};
  return { style: "background: color-mix(in srgb, var(--semi-color-danger) 6%, transparent)" };
}

const columns: DataTableColumns<ProofreadRecord> = [
  {
    title: "来源", key: "doc_source", width: 70,
    render: (r) => h(NTag, { size: "small", round: true, type: r.doc_source === "formal" ? "success" : "default", bordered: false },
      { default: () => (r.doc_source === "formal" ? "正式库" : "暂存库") }),
  },
  { title: "档号", key: "DH", width: 180, render: (r) => h("span", { class: "font-mono text-xs" }, r.DH || "—") },
  { title: "题名", key: "TM", minWidth: 220, ellipsis: { tooltip: true }, render: (r) => r.TM || "—" },
  { title: "年度", key: "ND", width: 64, render: (r) => (r.ND ? String(r.ND) : "—") },
  { title: "校对结果", key: "verdict", width: 240, render: renderVerdict },
  {
    title: "操作", key: "actions", width: 170, fixed: "right" as const,
    render: (r) => h("div", { class: "flex gap-1.5" }, [
      h(NButton, {
        size: "tiny",
        tertiary: r.verdict !== "flagged",
        secondary: r.verdict === "flagged",
        type: r.verdict === "flagged" ? "error" : "primary",
        disabled: !r.has_pdf,
        title: r.has_pdf ? "查看差异并逐项人工确认，保存前不会改动任何数据" : "该档案无 PDF 原文挂接",
        onClick: () => openDrawer(r),
      }, { default: () => (r.verdict === "flagged" ? "去确认" : "校正") }),
      h(NButton, {
        size: "tiny", tertiary: true,
        disabled: !r.has_pdf,
        title: r.has_pdf ? "查看原文" : "该档案暂无数字化原文",
        onClick: () => router.push(`/archive/reader?id=${r.id}`),
      }, { default: () => "查看原文" }),
    ]),
  },
];

// ── 发起校对 ──────────────────────────────────────────────────────────────────
const starting = ref(false);
const forceRerun = ref(false);

async function confirmStart() {
  starting.value = true;
  try {
    const res = await ProofreadAPI.preview(docSource.value, buildQuery());
    if (res.code !== 0) return message.error(res.message);
    const p = res.data;
    if (!p.with_pdf) return message.warning("当前范围内没有已挂接 PDF 原文的档案，无法校对");
    forceRerun.value = false;
    const label = scopeLabel();
    dialog.warning({
      title: "开始智能校对",
      content: () =>
        h("div", { class: "flex flex-col gap-2 text-[13px] leading-relaxed" }, [
          h("div", {}, [`范围：${label}`]),
          h("div", {}, [
            "本次将校对 ",
            h("strong", {}, String(p.with_pdf)),
            " 件档案",
            p.need_ocr ? `（其中 ${p.need_ocr} 件将先自动 OCR 识别原文）` : "",
            p.no_pdf ? `；另有 ${p.no_pdf} 件无原文挂接，已排除` : "",
            "。",
          ]),
          h("div", { class: "text-[12px]", style: "color:var(--semi-color-text-3)" },
            "任务在后台执行，可随时离开本页，完成后会收到站内通知。原文未变的条目自动复用上次抽取结果，不重复调用 AI。"),
          h(NCheckbox, {
            checked: forceRerun.value,
            onUpdateChecked: (v: boolean) => { forceRerun.value = v; },
          }, { default: () => "强制重新校对（无视抽取缓存，全部重跑 AI）" }),
        ]),
      positiveText: "开始校对",
      negativeText: "取消",
      onPositiveClick: async () => {
        const r = await ProofreadAPI.start(docSource.value, buildQuery(), label, forceRerun.value);
        if (r.code !== 0) return message.error(r.message);
        if (!r.data.ok) return message.error(r.data.reason || "发起失败");
        message.success(`已发起校对，共 ${r.data.total} 件`);
        await refreshActive();
      },
    });
  } finally {
    starting.value = false;
  }
}

// ── 批次进度（轮询）/ 历史 ────────────────────────────────────────────────────
const activeBatch = ref<ProofreadBatch | null>(null);
const progressPct = computed(() =>
  activeBatch.value && activeBatch.value.total
    ? Math.round((activeBatch.value.processed / activeBatch.value.total) * 100)
    : 0,
);
let pollTimer: ReturnType<typeof setInterval> | null = null;

function startPolling() {
  stopPolling();
  pollTimer = setInterval(pollActive, 2500);
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

async function pollActive() {
  if (!activeBatch.value) return stopPolling();
  const res = await ProofreadAPI.batch(activeBatch.value.id);
  if (res.code !== 0) return;
  const b = res.data;
  if (b.status === "running") {
    activeBatch.value = b;
    return;
  }
  stopPolling();
  activeBatch.value = null;
  latestBatch.value = b;
  if (b.status === "done") {
    if (b.flagged > 0) {
      message.warning(`校对完成：共 ${b.total} 件，发现 ${b.flagged} 件与原文不符，等待人工确认`);
    } else {
      message.success(`校对完成：共 ${b.total} 件，著录与原文相符`);
    }
  } else if (b.status === "canceled") {
    message.info("校对已取消");
  }
  load();
}

const latestBatch = ref<ProofreadBatch | null>(null);

async function refreshActive() {
  const res = await ProofreadAPI.batches({ limit: 1 });
  if (res.code !== 0) return;
  const latest = res.data.items[0];
  latestBatch.value = latest && latest.status !== "running" ? latest : null;
  if (latest && latest.status === "running") {
    activeBatch.value = latest;
    startPolling();
  } else {
    activeBatch.value = null;
    stopPolling();
  }
}

function cancelBatch() {
  if (!activeBatch.value) return;
  const id = activeBatch.value.id;
  dialog.warning({
    title: "取消校对",
    content: "确认取消当前运行中的校对任务？已出结果的条目将保留。",
    positiveText: "确认取消",
    negativeText: "继续校对",
    onPositiveClick: async () => {
      const r = await ProofreadAPI.cancel(id);
      if (r.code !== 0 || !r.data.ok) return message.error(r.data?.reason || r.message || "取消失败");
      message.info("已取消");
      await refreshActive();
      load();
    },
  });
}

// 历史批次
const batchShow = ref(false);
const batches = ref<ProofreadBatch[]>([]);
const batchLoading = ref(false);
const BATCH_STATUS: Record<string, { label: string; type: "default" | "info" | "warning" | "error" | "success" }> = {
  running: { label: "运行中", type: "info" },
  done: { label: "已完成", type: "success" },
  canceled: { label: "已取消", type: "default" },
  failed: { label: "失败", type: "error" },
};
const batchColumns: DataTableColumns<ProofreadBatch> = [
  { title: "范围", key: "scope_label", minWidth: 160, ellipsis: { tooltip: true }, render: (b) => b.scope_label || "全库" },
  { title: "件数", key: "total", width: 64, render: (b) => h("span", { class: "tabular-nums" }, String(b.total)) },
  {
    title: "结果", key: "result", width: 170,
    render: (b) => h("span", { class: "text-[12px] tabular-nums", style: "color:var(--semi-color-text-2)" },
      `待确认 ${b.flagged} · 相符 ${b.consistent}${b.no_text ? ` · 无法识别 ${b.no_text}` : ""}${b.failed ? ` · 失败 ${b.failed}` : ""}`),
  },
  {
    title: "状态", key: "status", width: 84,
    render: (b) => {
      const m = BATCH_STATUS[b.status] ?? BATCH_STATUS.done;
      return h(NTag, { size: "small", round: true, type: m.type, bordered: false }, { default: () => m.label });
    },
  },
  {
    title: "时间", key: "started_at", width: 140,
    render: (b) => h("span", { class: "text-[12px] tabular-nums", style: "color:var(--semi-color-text-3)" },
      b.started_at ? b.started_at.slice(0, 16).replace("T", " ") : "—"),
  },
];

async function loadBatches() {
  batchLoading.value = true;
  try {
    const res = await ProofreadAPI.batches({ limit: 50 });
    if (res.code === 0) batches.value = res.data.items;
  } finally {
    batchLoading.value = false;
  }
}
watch(batchShow, (v) => { if (v) loadBatches(); });

// ── 整改（复用智能著录抽屉） ──────────────────────────────────────────────────
const drawerShow = ref(false);
const target = ref<{ id: string; doc_source: "staging" | "formal"; DH?: string; TM: string; category_id?: string | null } | null>(null);

function openDrawer(r: ProofreadRecord) {
  target.value = { id: r.id, doc_source: r.doc_source, DH: r.DH, TM: r.TM, category_id: r.category_id ?? null };
  drawerShow.value = true;
}

async function onResolved() {
  // 写库成功后：最新存疑结果标记「已整改」并刷新表格
  if (target.value) await ProofreadAPI.resolve(target.value.id);
  load();
}

// ── 生命周期（Tab 保活下的轮询启停） ──────────────────────────────────────────
onMounted(async () => {
  await Promise.all([load(), refreshActive()]);
});
onActivated(() => { if (activeBatch.value) startPolling(); refreshActive(); });
onDeactivated(stopPolling);
onBeforeUnmount(stopPolling);
</script>
