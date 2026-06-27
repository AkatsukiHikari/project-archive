<template>
  <div class="flex flex-col gap-3 min-h-0 flex-1">
    <div class="flex items-start justify-between gap-3">
      <AdminPageHeader
        title="档案查询"
        description="按字段检索或原文全文检索，支持 AI 智能解读"
        icon="heroicons:magnifying-glass-circle"
      />
      <!-- 当前办理人（点头像看详情，可办结） -->
      <div
        v-if="currentApp"
        class="flex items-center gap-2 pro-card px-3 py-2 cursor-pointer shrink-0"
        @click="showPerson = true"
      >
        <PersonAvatar :name="currentApp.applicant_name" :size="36" />
        <div class="flex flex-col">
          <span class="text-[13px] font-medium leading-tight" style="color:var(--semi-color-text-0)">{{ currentApp.applicant_name }}</span>
          <span class="text-[11px]" style="color:var(--semi-color-text-3)">办理中 · 调阅篮 {{ currentApp.item_count }} 件</span>
        </div>
        <Icon name="heroicons:chevron-down" class="w-4 h-4" style="color:var(--semi-color-text-3)" />
      </div>
    </div>

    <!-- ── 检索区 ─────────────────────────────────────────── -->
    <div class="pro-card p-5 flex flex-col gap-4">
      <!-- 检索模式 -->
      <div class="flex items-center gap-2">
        <button
          v-for="m in modes"
          :key="m.value"
          class="px-3.5 py-1.5 rounded-lg text-[13px] font-medium border-none cursor-pointer transition-colors"
          :style="mode === m.value
            ? 'background:oklch(var(--p)/0.12);color:oklch(var(--p))'
            : 'background:var(--semi-color-fill-0);color:var(--semi-color-text-2)'"
          @click="switchMode(m.value)"
        >
          <Icon :name="m.icon" class="w-4 h-4 mr-1 inline-block align-text-bottom" />{{ m.label }}
        </button>
        <div class="flex-1" />
        <span class="text-sm text-gray-500">共 <strong>{{ total }}</strong> 条</span>
      </div>

      <!-- 大检索框 -->
      <div class="flex items-stretch gap-3">
        <NInput
          v-model:value="keyword"
          :placeholder="mode === 'fulltext'
            ? '输入内容关键词，检索档案原文 OCR 全文（如「防汛」「征地补偿」）'
            : '题名 / 责任者 / 档号'"
          size="large"
          clearable
          class="flex-1"
          @keydown.enter="search"
        >
          <template #prefix><Icon name="heroicons:magnifying-glass" class="w-5 h-5 text-gray-400" /></template>
        </NInput>
        <NButton type="primary" size="large" :loading="loading" @click="search">
          <template #icon><Icon name="heroicons:magnifying-glass" class="w-4 h-4" /></template>
          检索
        </NButton>
        <NButton size="large" tertiary @click="reset">重置</NButton>
        <NButton v-if="mode === 'field'" size="large" text type="primary" @click="advanced = !advanced">
          <Icon :name="advanced ? 'heroicons:chevron-up' : 'heroicons:adjustments-horizontal'" class="w-4 h-4 mr-1" />
          {{ advanced ? "收起" : "高级查询" }}
        </NButton>
      </div>


      <!-- 字段高级查询（仅字段检索模式） -->
      <div v-show="mode === 'field' && advanced" class="grid grid-cols-2 lg:grid-cols-4 gap-x-4 gap-y-3 pt-1 border-t" style="border-color: var(--semi-color-border)">
        <Field label="题名"><NInput v-model:value="form.TM" placeholder="题名关键字" clearable /></Field>
        <Field label="责任者"><NInput v-model:value="form.RZZ" placeholder="责任者" clearable /></Field>
        <Field label="档号"><NInput v-model:value="form.DH" placeholder="档号" clearable /></Field>
        <Field label="全宗"><NSelect v-model:value="form.fonds_id" :options="fondsOptions" placeholder="全部全宗" clearable filterable /></Field>
        <Field label="门类"><NSelect v-model:value="form.category_id" :options="categoryOptions" placeholder="全部门类" clearable filterable /></Field>
        <Field label="密级"><NSelect v-model:value="form.MJ" :options="mjOptions" placeholder="全部" clearable :disabled="publicOnly" /></Field>
        <Field label="保管期限"><NSelect v-model:value="form.BGQX" :options="bgqxOptions" placeholder="全部" clearable /></Field>
        <Field label="年度">
          <div class="flex items-center gap-1">
            <NInputNumber v-model:value="form.ND_from" :show-button="false" placeholder="起" class="flex-1" />
            <span class="text-gray-400">~</span>
            <NInputNumber v-model:value="form.ND_to" :show-button="false" placeholder="止" class="flex-1" />
          </div>
        </Field>
      </div>
    </div>

    <!-- ── 目录导航树 + 结果表 ─────────────────────────────── -->
    <div class="flex gap-3 flex-1 min-h-0">
      <!-- 目录导航：门类 → 全宗号 → 年度，逐层点选过滤 -->
      <div
        v-if="navOpen"
        class="pro-card p-3 flex flex-col gap-2 shrink-0"
        style="width: 248px"
      >
        <div class="flex items-center justify-between">
          <span class="text-[13px] font-medium" style="color:var(--semi-color-text-0)">目录导航</span>
          <button class="bg-transparent border-none cursor-pointer p-0.5" style="color:var(--semi-color-text-3)" title="收起" @click="navOpen = false">
            <Icon name="heroicons:chevron-double-left" class="w-4 h-4" />
          </button>
        </div>
        <p class="text-[11px] m-0" style="color:var(--semi-color-text-3)">门类 / 全宗号 / 年度 逐层点选</p>
        <div class="flex-1 overflow-auto">
          <NTree
            block-line
            selectable
            expand-on-click
            key-field="key"
            label-field="label"
            :data="navData"
            :on-load="onLoadNav"
            :selected-keys="selectedNavKeys"
            @update:selected-keys="onNavSelect"
          />
        </div>
        <NButton v-if="navScopeLabel" size="tiny" tertiary block @click="clearNav">
          <template #icon><Icon name="heroicons:x-mark" class="w-3.5 h-3.5" /></template>
          清除目录筛选
        </NButton>
      </div>
      <button
        v-else
        class="pro-card shrink-0 flex flex-col items-center gap-2 py-3 cursor-pointer bg-transparent"
        style="width: 36px; color:var(--semi-color-text-2)"
        title="展开目录导航"
        @click="navOpen = true"
      >
        <Icon name="heroicons:bars-3" class="w-4 h-4" />
        <span class="text-[11px]" style="writing-mode:vertical-rl">目录导航</span>
      </button>

      <!-- 结果表 -->
      <div class="pro-card p-4 flex-1 min-w-0 min-h-0 flex flex-col gap-3">
        <div class="flex items-center gap-3">
          <NTag v-if="navScopeLabel" size="small" type="info" round closable @close="clearNav">
            目录：{{ navScopeLabel }}
          </NTag>
          <template v-if="currentApp">
            <span class="text-sm" style="color:var(--semi-color-text-2)">已选 <strong>{{ selected.size }}</strong> 件</span>
            <NButton size="small" type="primary" :disabled="selected.size === 0" @click="addToBasket">
              <template #icon><Icon name="heroicons:shopping-bag" class="w-4 h-4" /></template>
              加入调阅篮
            </NButton>
            <div class="flex-1" />
            <NButton size="small" type="success" @click="completeApp">
              <template #icon><Icon name="heroicons:check-circle" class="w-4 h-4" /></template>
              办理完成
            </NButton>
          </template>
        </div>
        <ProTable :columns="columns" :data="rows" :loading="loading" :page-size="0" size="small" :scroll-x="1320" />
        <div class="flex justify-end">
          <NPagination v-model:page="page" :page-count="pageCount" :page-size="pageSize" show-quick-jumper @update:page="load" />
        </div>
      </div>
    </div>

    <!-- 档案详情抽屉 -->
    <NDrawer v-model:show="showDetail" :width="560" placement="right">
      <NDrawerContent :title="`档案详情 · ${detail?.DH || ''}`" closable>
        <div v-if="detail" class="flex flex-col gap-4">
          <table class="w-full text-[13px] border-collapse">
            <tbody>
              <tr v-for="f in detailFields" :key="f.label" class="border-b" style="border-color: var(--semi-color-border)">
                <th class="text-left align-top py-2 pr-3 font-medium whitespace-nowrap" style="width:96px;color:var(--semi-color-text-3)">{{ f.label }}</th>
                <td class="py-2 break-words" :class="f.mono ? 'font-mono' : ''" style="color:var(--semi-color-text-0)">{{ f.value || "—" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <template #footer>
          <div class="flex items-center gap-2">
            <NButton type="primary" ghost @click="askAI(detail)">
              <template #icon><Icon name="heroicons:sparkles" class="w-4 h-4" /></template>
              让 AI 解读
            </NButton>
            <div class="flex-1" />
            <NButton @click="showDetail = false">关闭</NButton>
            <NButton type="primary" :disabled="!detail?.attachment_count" @click="openReader()">
              <template #icon><Icon name="heroicons:document-text" class="w-4 h-4" /></template>
              {{ detail?.attachment_count ? "查看原文" : "无原文" }}
            </NButton>
          </div>
        </template>
      </NDrawerContent>
    </NDrawer>

    <!-- 办理人详情抽屉（复用组件，与利用申请页一致） -->
    <NDrawer v-model:show="showPerson" :width="480" placement="right">
      <NDrawerContent :title="`利用登记 · ${currentApp?.reg_no || ''}`" closable>
        <ApplicationDetailPanel :app-id="appId" :show-actions="false" @changed="reloadApp" />
      </NDrawerContent>
    </NDrawer>

    <ArchiveInterpretDrawer v-model:show="interpretShow" :archive-id="interpretId" :title="interpretTitle" />
  </div>
</template>

<script setup lang="tsx">
import { ref, reactive, computed, onMounted, watch, h } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NInput, NInputNumber, NSelect, NButton, NPagination, NTag, NCheckbox, NDrawer, NDrawerContent, NTree, useMessage, useDialog } from "naive-ui";
import type { DataTableColumns, TreeOption } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { PersonAvatar, ApplicationDetailPanel, ArchiveInterpretDrawer } from "@/components/archive";
import { FondsAPI, CategoryAPI, ArchiveAPI } from "@/api/repository";
import type { Fonds, ArchiveCategory, Archive, ArchiveListParams } from "@/api/repository";
import { UtilizationAPI } from "@/api/utilization";
import type { UtilApplication, ItemIn, FullTextHit } from "@/api/utilization";
import { AppraisalAPI } from "@/api/appraisal";
import type { ArchiveConclusion } from "@/api/appraisal";

definePageMeta({ layout: "archive", middleware: "auth" });

const route = useRoute();
const router = useRouter();
const message = useMessage();
const dialog = useDialog();

const appId = computed(() => (route.query.app ? String(route.query.app) : null));
const publicOnly = computed(() => !!appId.value);  // 社会大众查档：仅公开

const mjOptions = [
  { label: "无", value: "无" }, { label: "秘密", value: "秘密" },
  { label: "机密", value: "机密" }, { label: "绝密", value: "绝密" }, { label: "绝密", value: "top_secret" },
];
const bgqxOptions = [{ label: "永久", value: "permanent" }, { label: "长期", value: "long" }, { label: "短期", value: "short" }];
const MJ_LABEL: Record<string, string> = { "无": "无", "秘密": "秘密", "机密": "机密", "绝密": "绝密", public: "无", internal: "无", secret: "秘密", confidential: "机密", top_secret: "绝密" };
const BGQX_LABEL: Record<string, string> = { permanent: "永久", long: "长期", short: "短期" };
const MJ_TONE: Record<string, "default" | "warning" | "error"> = { "无": "default", "秘密": "warning", "机密": "error", "绝密": "error", public: "default", internal: "default", secret: "warning", confidential: "error", top_secret: "error" };

const Field = (props: { label: string }, { slots }: { slots: { default?: () => unknown } }) =>
  h("div", { class: "flex flex-col gap-1" }, [h("span", { class: "text-xs text-gray-500" }, props.label), slots.default?.()]);

const advanced = ref(false);
const keyword = ref("");  // 主检索框（字段模式=关键字；全文模式=全文词）
const mode = ref<"field" | "fulltext">("field");
const modes = [
  { value: "field" as const, label: "字段检索", icon: "heroicons:bars-3-bottom-left" },
  { value: "fulltext" as const, label: "全文检索", icon: "heroicons:document-magnifying-glass" },
];
const form = reactive<ArchiveListParams>({
  keyword: "", TM: "", RZZ: "", DH: "",
  fonds_id: undefined, category_id: undefined, MJ: undefined, BGQX: undefined,
  ND_from: undefined, ND_to: undefined,
});

// 全文命中：archive_id → { tm: 题名高亮html, snippet: 原文命中片段html }
const ftHits = ref<Record<string, { tm?: string; snippet?: string }>>({});
// 是否处于"全文检索结果"状态（已输入关键词并检索）；空查询/字段模式下为 false
const ftActive = ref(false);

const HL_OPEN = '<span style="color:#e5484d;font-weight:700">';

// 把 ES 高亮标签 <em> 渲染成红色关键词
function redHi(html: string): string {
  return html.replace(/<em>/g, HL_OPEN).replace(/<\/em>/g, "</span>");
}

function escapeHtml(s: string): string {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] as string));
}

// 字段检索：客户端把命中的查询词在文本里标红（字段查询走 DB ILIKE，无 ES 高亮）
function markTerms(text: string | null | undefined, terms: (string | undefined)[]): string {
  if (!text) return "—";
  const safe = escapeHtml(text);
  const valid = terms.filter((t): t is string => !!t && !!t.trim()).map((t) => t.trim());
  if (!valid.length) return safe;
  const pattern = valid.map((t) => t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&")).join("|");
  try {
    return safe.replace(new RegExp(`(${pattern})`, "gi"), `${HL_OPEN}$1</span>`);
  } catch {
    return safe;
  }
}

// 当前字段检索已应用的查询词（检索时快照，结果高亮用，不随输入框实时变化）
const fieldTerms = ref<{ keyword?: string; TM?: string; RZZ?: string; DH?: string }>({});

// ── 目录导航树（门类 → 全宗号 → 年度，逐层懒加载点选过滤）──────────────────
const navOpen = ref(true);
const navData = ref<TreeOption[]>([]);
const selectedNavKeys = ref<string[]>([]);
const navScopeLabel = ref("");

async function loadNavRoot() {
  const res = await ArchiveAPI.navCategories();
  navData.value = (res.data ?? []).map((c) => ({
    key: `c:${c.category_id}`,
    label: `${c.name}（${c.count}）`,
    isLeaf: false,
    meta: { level: "category", category_id: c.category_id, name: c.name },
  } as TreeOption));
}

async function onLoadNav(node: TreeOption): Promise<void> {
  const meta = (node.meta ?? {}) as Record<string, string>;
  if (meta.level === "category") {
    const res = await ArchiveAPI.navFonds(meta.category_id);
    node.children = (res.data ?? []).map((f) => ({
      key: `f:${meta.category_id}:${f.fonds_id}`,
      label: `${f.qzh}（${f.count}）`,
      isLeaf: false,
      meta: { level: "fonds", category_id: meta.category_id, fonds_id: f.fonds_id, qzh: f.qzh, name: meta.name },
    } as TreeOption));
  } else if (meta.level === "fonds") {
    const res = await ArchiveAPI.navYears(meta.category_id, meta.fonds_id);
    node.children = (res.data ?? []).map((y) => ({
      key: `y:${meta.category_id}:${meta.fonds_id}:${y.year}`,
      label: `${y.year} 年（${y.count}）`,
      isLeaf: true,
      meta: { level: "year", category_id: meta.category_id, fonds_id: meta.fonds_id, year: y.year, qzh: meta.qzh, name: meta.name },
    } as TreeOption));
  }
}

function onNavSelect(keys: string[], _opt: unknown, extra: { node: TreeOption | null }) {
  selectedNavKeys.value = keys;
  const node = extra.node;
  if (!node) { return; }
  const meta = (node.meta ?? {}) as Record<string, string | number>;
  // 目录导航是字段过滤：切到字段模式，按层级设置 门类/全宗/年度
  mode.value = "field";
  keyword.value = "";
  form.category_id = String(meta.category_id);
  form.fonds_id = meta.fonds_id ? String(meta.fonds_id) : undefined;
  form.ND_from = undefined;
  form.ND_to = undefined;
  if (meta.level === "year") {
    form.ND_from = Number(meta.year);
    form.ND_to = Number(meta.year);
    navScopeLabel.value = `${meta.name} / ${meta.qzh} / ${meta.year}年`;
  } else if (meta.level === "fonds") {
    navScopeLabel.value = `${meta.name} / ${meta.qzh}`;
  } else {
    navScopeLabel.value = String(meta.name);
  }
  page.value = 1;
  load();
}

function clearNav() {
  selectedNavKeys.value = [];
  navScopeLabel.value = "";
  form.category_id = undefined;
  form.fonds_id = undefined;
  form.ND_from = undefined;
  form.ND_to = undefined;
  page.value = 1;
  load();
}

function switchMode(m: "field" | "fulltext") {
  if (mode.value === m) return;
  mode.value = m;
  ftHits.value = {};
  ftActive.value = false;
  page.value = 1;
  load();
}

// ── 选项 / 映射 ───────────────────────────────────────────────────
const fondsList = ref<Fonds[]>([]);
const categoryMap = ref<Record<string, string>>({});
const fondsOptions = computed(() => fondsList.value.map((f) => ({ label: `${f.fonds_code} - ${f.name}`, value: f.id })));
const categoryOptions = ref<{ label: string; value: string }[]>([]);
const catName = (id: string) => categoryMap.value[id] ?? id.slice(0, 8);
// 门类扩展字段 拼音码 → 中文标签（合并所有门类的 field_schema）
const extLabel = ref<Record<string, string>>({});

// ── 当前办理人 ────────────────────────────────────────────────────
const currentApp = ref<UtilApplication | null>(null);
const showPerson = ref(false);
async function reloadApp() {
  if (!appId.value) { currentApp.value = null; return; }
  currentApp.value = (await UtilizationAPI.get(appId.value)).data;
}

// ── 列表（服务端分页） ────────────────────────────────────────────
const loading = ref(false);
const rows = ref<Archive[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)));
const selected = ref<Set<string>>(new Set());

function buildParams(): ArchiveListParams {
  const clean = (v?: string) => (v && v.trim() ? v.trim() : undefined);
  return {
    keyword: clean(keyword.value), TM: clean(form.TM), RZZ: clean(form.RZZ), DH: clean(form.DH),
    fonds_id: form.fonds_id || undefined, category_id: form.category_id || undefined,
    // 对外查档（从利用申请进入）：仅检索无密级档案
    MJ: publicOnly.value ? "无" : (form.MJ || undefined),
    BGQX: form.BGQX || undefined,
    ND_from: form.ND_from ?? undefined, ND_to: form.ND_to ?? undefined,
    page: page.value, page_size: pageSize.value,
  };
}

async function loadField() {
  const res = await ArchiveAPI.list(buildParams());
  rows.value = res.data.items;
  total.value = res.data.total;
  ftHits.value = {};
  ftActive.value = false;
  // 快照当前查询词，供结果命中标红
  fieldTerms.value = {
    keyword: keyword.value.trim() || undefined,
    TM: form.TM?.trim() || undefined,
    RZZ: form.RZZ?.trim() || undefined,
    DH: form.DH?.trim() || undefined,
  };
}

async function loadFullText() {
  const q = keyword.value.trim();
  // 未输入关键词时，显示默认档案列表（与字段模式一致），命中高亮留空
  if (!q) { await loadField(); return; }
  const res = await UtilizationAPI.search({
    q,
    public_only: publicOnly.value,
    skip: (page.value - 1) * pageSize.value,
    limit: pageSize.value,
  });
  if (res.code !== 0) { message.error(res.message); return; }
  const hits = res.data.hits ?? [];
  // 复用 Archive 行结构渲染表格
  rows.value = hits.map((h2: FullTextHit) => ({
    id: h2.id, DH: h2.DH ?? undefined, TM: h2.TM, RZZ: h2.RZZ ?? undefined,
    ND: h2.ND ?? undefined, QZH: h2.QZH ?? "", category_id: h2.catalog_id ?? "",
    MJ: h2.MJ ?? "无", BGQX: h2.BGQX ?? "", status: "archived",
    fonds_id: "", embedding_status: "done", attachment_count: 0,
  } as Archive));
  total.value = res.data.total;
  ftHits.value = Object.fromEntries(
    hits.map((h2) => [h2.id, {
      tm: h2.highlight?.TM?.[0],
      snippet: (h2.highlight?.full_text ?? []).join(" … "),
    }]),
  );
  ftActive.value = true;
}

async function load() {
  loading.value = true;
  try {
    if (mode.value === "fulltext") await loadFullText();
    else await loadField();
  } finally {
    loading.value = false;
  }
}
function search() { page.value = 1; load(); }

// 从路由 query 带入检索条件（AI 引用点击：?DH=档号 或 ?q=关键字）
function applyRouteQuery(): boolean {
  const dh = route.query.DH ? String(route.query.DH) : "";
  const q = route.query.q ? String(route.query.q) : "";
  if (!dh && !q) return false;
  mode.value = "field";
  selectedNavKeys.value = [];
  navScopeLabel.value = "";
  form.DH = dh;
  keyword.value = dh ? "" : q;
  page.value = 1;
  return true;
}
function reset() {
  keyword.value = "";
  Object.assign(form, { keyword: "", TM: "", RZZ: "", DH: "", fonds_id: undefined, category_id: undefined, MJ: undefined, BGQX: undefined, ND_from: undefined, ND_to: undefined });
  selectedNavKeys.value = [];
  navScopeLabel.value = "";
  page.value = 1;
  rows.value = [];
  total.value = 0;
  ftHits.value = {};
  ftActive.value = false;
  load();
}

function toggle(id: string, checked: boolean) {
  const s = new Set(selected.value);
  if (checked) s.add(id); else s.delete(id);
  selected.value = s;
}
function toggleAll(checked: boolean) {
  selected.value = checked ? new Set(rows.value.map((r) => r.id)) : new Set();
}
const allChecked = computed(() => rows.value.length > 0 && rows.value.every((r) => selected.value.has(r.id)));

const actionCol = {
  title: "操作", key: "actions", width: 180, fixed: "right" as const,
  render: (r: Archive) => h("div", { class: "flex gap-1.5" }, [
    h(NButton, { size: "small", tertiary: true, onClick: () => openDetail(r) }, () => "详情"),
    h(NButton, {
      size: "small", tertiary: true, type: "primary",
      disabled: !r.attachment_count,
      onClick: () => openReaderFor(r),
    }, () => (r.attachment_count ? "原文" : "无原文")),
    h(NButton, {
      size: "small", tertiary: true, type: "primary",
      onClick: () => askAI(r),
    }, () => "AI 解读"),
  ]),
};

const selCol = {
  key: "_sel", width: 44,
  title: () => h(NCheckbox, { checked: allChecked.value, onUpdateChecked: (c: boolean) => toggleAll(c) }),
  render: (r: Archive) => h(NCheckbox, { checked: selected.value.has(r.id), onUpdateChecked: (c: boolean) => toggle(r.id, c) }),
};

// 字段检索表头（命中的查询词客户端标红）
const fieldColumns: DataTableColumns<Archive> = [
  {
    title: "档号", key: "DH", width: 190,
    render: (r) => h("span", { class: "font-mono text-[12px]", innerHTML: markTerms(r.DH, [fieldTerms.value.keyword, fieldTerms.value.DH]) }),
  },
  {
    title: "题名", key: "TM", minWidth: 260,
    render: (r) => h("span", { class: "text-[13px]", innerHTML: markTerms(r.TM, [fieldTerms.value.keyword, fieldTerms.value.TM]) }),
  },
  {
    title: "责任者", key: "RZZ", width: 120,
    render: (r) => h("span", { innerHTML: markTerms(r.RZZ, [fieldTerms.value.keyword, fieldTerms.value.RZZ]) }),
  },
  { title: "年度", key: "ND", width: 70, render: (r) => r.ND ?? "—" },
  { title: "全宗号", key: "QZH", width: 90 },
  { title: "门类", key: "category_id", width: 200, render: (r) => catName(r.category_id) },
  { title: "密级", key: "MJ", width: 80, render: (r) => h(NTag, { size: "small", type: MJ_TONE[r.MJ] ?? "default" }, () => MJ_LABEL[r.MJ] ?? r.MJ) },
  { title: "保管期限", key: "BGQX", width: 90, render: (r) => BGQX_LABEL[r.BGQX] ?? r.BGQX },
  actionCol,
];

// 全文检索表头：突出"命中内容"，关键词标红
const fulltextColumns: DataTableColumns<Archive> = [
  { title: "档号", key: "DH", width: 170, render: (r) => h("span", { class: "font-mono text-[12px]" }, r.DH || "—") },
  {
    title: "题名", key: "TM", width: 220, ellipsis: { tooltip: true },
    render: (r) => {
      const tm = ftHits.value[r.id]?.tm;
      return h("span", { class: "text-[13px]", innerHTML: tm ? redHi(tm) : r.TM });
    },
  },
  {
    title: "命中内容（原文）", key: "_snippet", minWidth: 360,
    render: (r) => {
      const snip = ftHits.value[r.id]?.snippet;
      if (!snip) {
        return h("span", { class: "text-[12px]", style: "color:var(--semi-color-text-3)" }, "（命中题名）");
      }
      return h("span", {
        class: "text-[12.5px] leading-relaxed",
        style: "color:var(--semi-color-text-1)",
        innerHTML: "… " + redHi(snip) + " …",
      });
    },
  },
  { title: "年度", key: "ND", width: 64, render: (r) => r.ND ?? "—" },
  { title: "全宗号", key: "QZH", width: 80 },
  actionCol,
];

const columns = computed<DataTableColumns<Archive>>(() => {
  // 依赖 fieldTerms/ftHits：检索后查询词变化时返回新数组，强制表格重渲染高亮
  void fieldTerms.value;
  void ftHits.value;
  const base = (mode.value === "fulltext" && ftActive.value) ? fulltextColumns : fieldColumns;
  return appId.value ? [selCol, ...base] : [...base];
});

// ── 调阅篮 / 办结 ─────────────────────────────────────────────────
async function addToBasket() {
  if (!appId.value || selected.value.size === 0) return;
  const items: ItemIn[] = rows.value
    .filter((r) => selected.value.has(r.id))
    .map((r) => ({ archive_id: r.id, DH: r.DH ?? null, TM: r.TM, RZZ: r.RZZ ?? null, ND: r.ND ?? null, QZH: r.QZH }));
  const res = await UtilizationAPI.addItems(appId.value, items);
  message.success(`已加入 ${res.data.added} 件（去重后）`);
  selected.value = new Set();
  await reloadApp();
}
function completeApp() {
  if (!appId.value) return;
  dialog.success({
    title: "办理完成",
    content: `确认为「${currentApp.value?.applicant_name}」办结本次利用？调阅篮共 ${currentApp.value?.item_count ?? 0} 件。`,
    positiveText: "确认办结", negativeText: "取消",
    onPositiveClick: async () => {
      await UtilizationAPI.complete(appId.value!);
      message.success("已办理完成");
      router.push("/archive/utilization/apply");
    },
  });
}

// ── 档案详情抽屉 ──────────────────────────────────────────────────
const showDetail = ref(false);
const detail = ref<Archive | null>(null);
const conclusion = ref<ArchiveConclusion | null>(null);
const detailFields = computed(() => {
  const a = detail.value;
  if (!a) return [];
  return [
    { label: "档号", value: a.DH, mono: true },
    { label: "题名", value: a.TM, mono: false },
    { label: "责任者", value: a.RZZ, mono: false },
    { label: "年度", value: a.ND ? `${a.ND} 年` : "", mono: false },
    { label: "文件日期", value: a.WJRQ, mono: false },
    { label: "页数", value: a.YS ? `${a.YS} 页` : "", mono: false },
    { label: "全宗号", value: a.QZH, mono: true },
    { label: "门类", value: catName(a.category_id), mono: false },
    { label: "密级", value: MJ_LABEL[a.MJ] ?? a.MJ, mono: false },
    { label: "保管期限", value: BGQX_LABEL[a.BGQX] ?? a.BGQX, mono: false },
    { label: "开放状态", value: a.KFZT ?? "未鉴定", mono: false },
    ...(conclusion.value ? [
      { label: "鉴定日期", value: conclusion.value.appraised_at, mono: false },
      { label: "开放理由", value: conclusion.value.reason, mono: false },
      { label: "引用标准", value: conclusion.value.standard_code, mono: false },
      { label: "鉴定计划", value: conclusion.value.plan_name, mono: false },
    ] : []),
    ...Object.entries(a.ext_fields ?? {}).map(([k, v]) => ({
      label: extLabel.value[k] ?? k,   // 拼音码 → 门类字段中文标签（如 NFXM → 男方姓名）
      value: v == null ? "" : String(v),
      mono: false,
    })),
  ];
});
async function openDetail(r: Archive) {
  detail.value = r;
  conclusion.value = null;
  showDetail.value = true;
  // 鉴定结论（开放理由/日期/标准）关联查询，不读档案静态列
  if (r.KFZT) {
    const res = await AppraisalAPI.archiveConclusion(r.id);
    if (res.code === 0) conclusion.value = res.data;
  }
}
function openReader(id?: string) {
  const aid = id ?? detail.value?.id;
  if (aid) router.push(`/archive/reader?id=${aid}`);
}
function openReaderFor(r: Archive) { router.push(`/archive/reader?id=${r.id}`); }
const interpretShow = ref(false);
const interpretId = ref<string | null>(null);
const interpretTitle = ref("");
function askAI(r: Archive | null) {
  if (!r) return;
  interpretId.value = r.id;
  interpretTitle.value = `${r.DH || ""} ${r.TM || ""}`.trim();
  interpretShow.value = true;
}

onMounted(async () => {
  const [f, c] = await Promise.all([FondsAPI.list(), CategoryAPI.list()]);
  fondsList.value = f.data;
  categoryMap.value = Object.fromEntries(c.data.map((x: ArchiveCategory) => [x.id, `${x.code} - ${x.name}`]));
  categoryOptions.value = c.data.map((x: ArchiveCategory) => ({ label: `${x.code} - ${x.name}`, value: x.id }));
  // 合并所有门类 field_schema，建拼音码→中文标签映射
  const labels: Record<string, string> = {};
  for (const cat of c.data) {
    for (const fld of cat.field_schema ?? []) {
      if (fld.name && fld.label) labels[fld.name] = fld.label;
    }
  }
  extLabel.value = labels;
  await reloadApp();
  applyRouteQuery();
  await load();
  await loadNavRoot();
});

// 已打开的查阅页 Tab 再次被 AI 引用点击（同路径换 query，不重新挂载）→ 监听重查
watch(
  () => [route.query.DH, route.query.q],
  () => { if (applyRouteQuery()) load(); },
);
</script>
