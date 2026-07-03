<template>
  <div class="h-full overflow-y-auto">
    <div class="px-5 py-4 flex flex-col gap-4">
      <!-- 检索区 -->
      <div class="pro-card p-5 flex flex-col gap-3">
        <div class="inline-flex p-1 rounded-lg w-fit" style="background: var(--semi-color-fill-0)">
          <button
            v-for="m in modes"
            :key="m.value"
            class="px-4 py-1.5 rounded-md text-[13px] font-medium border-none cursor-pointer transition-all"
            :style="mode === m.value
              ? 'background: var(--semi-color-bg-0); color: oklch(var(--p)); box-shadow: 0 1px 2px rgba(0,0,0,.08)'
              : 'background: transparent; color: var(--semi-color-text-2)'"
            @click="switchMode(m.value)"
          >
            {{ m.label }}
          </button>
        </div>
        <div class="flex items-stretch gap-3">
          <NInput
            v-model:value="keyword"
            :placeholder="mode === 'fulltext' ? '检索档案数字化原文 OCR 全文（如：防汛、征地补偿）' : '检索题名 / 责任者 / 档号'"
            size="large"
            clearable
            class="flex-1"
            @keyup.enter="runSearch"
          >
            <template #prefix><Icon name="heroicons:magnifying-glass" class="w-5 h-5" style="color: var(--semi-color-text-3)" /></template>
          </NInput>
          <NButton type="primary" size="large" :loading="loading" @click="runSearch">检索</NButton>
          <NButton size="large" tertiary @click="resetAll">重置</NButton>
        </div>
      </div>

      <!-- 筛选条件 + 结果表 -->
      <div class="flex gap-4 items-start">
        <!-- 左：絞り込み条件 -->
        <aside class="w-64 shrink-0 pro-card overflow-hidden">
          <div class="px-4 py-3 flex items-center gap-2" style="border-bottom: 1px solid var(--semi-color-border)">
            <Icon name="heroicons:funnel" class="w-4 h-4" style="color: oklch(var(--p))" />
            <span class="text-[13px] font-semibold" style="color: var(--semi-color-text-0)">筛选条件</span>
          </div>
          <div
            v-for="f in facetOrder"
            :key="f"
            style="border-bottom: 1px solid var(--semi-color-border)"
            class="last:border-b-0"
          >
            <button
              class="w-full flex items-center justify-between px-4 py-2.5 bg-transparent border-none cursor-pointer"
              @click="toggleSection(f)"
            >
              <span class="text-[13px] font-medium" style="color: var(--semi-color-text-1)">{{ facetLabels[f] }}</span>
              <Icon :name="open[f] ? 'heroicons:chevron-up' : 'heroicons:chevron-down'" class="w-4 h-4" style="color: var(--semi-color-text-3)" />
            </button>
            <div v-show="open[f]" class="px-2 pb-2 flex flex-col gap-0.5">
              <button
                v-for="b in visibleFacet(f)"
                :key="String(b.value)"
                class="flex items-center gap-2 px-2 py-1.5 rounded-md text-[13px] border-none cursor-pointer text-left transition-colors"
                :style="isSelected(f, b.value)
                  ? 'background: oklch(var(--p)/0.1); color: oklch(var(--p))'
                  : 'background: transparent; color: var(--semi-color-text-1)'"
                @click="toggleFacet(f, b.value)"
              >
                <span
                  class="w-3.5 h-3.5 rounded-[3px] shrink-0 flex items-center justify-center"
                  :style="isSelected(f, b.value)
                    ? 'background: oklch(var(--p)); border: 1px solid oklch(var(--p))'
                    : 'border: 1px solid var(--semi-color-border)'"
                >
                  <Icon v-if="isSelected(f, b.value)" name="heroicons:check" class="w-2.5 h-2.5" style="color: oklch(var(--pc))" />
                </span>
                <span class="flex-1 truncate">{{ facetValueLabel(f, b.label) }}</span>
                <span class="text-[11px] tabular-nums shrink-0" style="color: var(--semi-color-text-3)">{{ b.count }}</span>
              </button>
              <button
                v-if="(facets[f] || []).length > FACET_LIMIT"
                class="text-[12px] px-2 py-1 bg-transparent border-none cursor-pointer text-left"
                style="color: oklch(var(--p))"
                @click="toggleExpand(f)"
              >
                {{ expanded[f] ? "收起" : `展开全部 ${facets[f].length} 项` }}
              </button>
              <div v-if="!(facets[f] || []).length" class="px-2 py-1 text-[12px]" style="color: var(--semi-color-text-3)">无</div>
            </div>
          </div>
        </aside>

        <!-- 右：结果表 -->
        <section class="flex-1 min-w-0 flex flex-col gap-3">
          <div class="flex items-center flex-wrap gap-2 min-h-[24px]">
            <span class="text-sm" style="color: var(--semi-color-text-2)">共 <strong style="color: var(--semi-color-text-0)">{{ total }}</strong> 件</span>
            <NTag v-for="chip in activeChips" :key="chip.key" size="small" round closable type="info" @close="toggleFacet(chip.field, chip.value)">
              {{ facetLabels[chip.field] }}：{{ facetValueLabel(chip.field, chip.label) }}
            </NTag>
            <NButton v-if="activeChips.length" size="tiny" text type="primary" @click="clearFacets">清除筛选</NButton>
          </div>

          <div class="pro-card p-2">
            <NDataTable
              :columns="activeColumns"
              :data="hits"
              :loading="loading"
              :pagination="pagination"
              :row-key="(r: SearchHit) => r.id"
              :bordered="false"
              :single-line="false"
              :scroll-x="activeScrollX"
              size="small"
              remote
              @update:page="onPage"
              @update:page-size="onPageSize"
            />
          </div>
        </section>
      </div>
    </div>

    <ArchiveInterpretDrawer v-model:show="interpretShow" :archive-id="interpretId" :title="interpretTitle" />

    <!-- 档案详情 -->
    <NDrawer v-model:show="detailShow" :width="560" placement="right">
      <NDrawerContent :title="`档案详情 · ${detailRow?.DH || detailRow?.TM || ''}`" closable>
        <div v-if="detailLoading" class="py-8 flex justify-center"><NSpin size="small" /></div>
        <div v-else-if="detail" class="flex flex-col gap-4">
          <table class="w-full text-[13px] border-collapse">
            <tbody>
              <tr
                v-for="f in detailFields"
                :key="f.label"
                class="border-b"
                style="border-color: var(--semi-color-border)"
              >
                <th class="text-left align-top py-2 pr-3 font-medium whitespace-nowrap" style="width:96px;color:var(--semi-color-text-3)">{{ f.label }}</th>
                <td class="py-2 break-words" :class="f.mono ? 'font-mono' : ''" style="color:var(--semi-color-text-0)">{{ f.value || "—" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <template #footer>
          <div class="flex w-full items-center gap-2">
            <NButton
              type="primary"
              :disabled="!detailRow?.has_source"
              :title="detailRow?.has_source ? '查看原文' : '该档案暂无数字化原文'"
              @click="detailRow && openReader(detailRow.id)"
            >
              <template #icon><Icon name="heroicons:document-magnifying-glass" class="w-4 h-4" /></template>
              查看原文
            </NButton>
            <div class="flex-1" />
            <NButton text type="primary" @click="detailRow && openInterpret(detailRow)">
              <template #icon><Icon name="heroicons:sparkles" class="w-4 h-4" /></template>
              AI 解读
            </NButton>
          </div>
        </template>
      </NDrawerContent>
    </NDrawer>
  </div>
</template>

<script setup lang="tsx">
import { computed, h, onMounted, reactive, ref } from "vue";
import { NButton, NDataTable, NDrawer, NDrawerContent, NInput, NSpin, NTag } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { SuperSearchAPI, type FacetValue, type SearchHit, type SearchMode } from "@/api/superSearch";
import { ArchiveAPI } from "@/api/repository";
import type { Archive } from "@/api/repository";
import { ArchiveInterpretDrawer } from "@/components/archive";

definePageMeta({ layout: "search" });
useHead({ title: "档案检索" });

const route = useRoute();

const modes = [
  { label: "字段检索", value: "field" as SearchMode },
  { label: "全文检索", value: "fulltext" as SearchMode },
];
const facetOrder = ["QZH", "ND", "category_id", "RZZ", "MJ", "BGQX"];
const facetLabels: Record<string, string> = {
  QZH: "全宗号", ND: "年度", category_id: "门类", RZZ: "责任者", MJ: "密级", BGQX: "保管期限",
};
const FACET_LIMIT = 8;

const keyword = ref("");
const mode = ref<SearchMode>("field");
const selected = reactive<Record<string, (string | number)[]>>({
  QZH: [], ND: [], RZZ: [], MJ: [], BGQX: [], category_id: [],
});
const open = reactive<Record<string, boolean>>(
  Object.fromEntries(facetOrder.map((f) => [f, true])),
);
const expanded = reactive<Record<string, boolean>>({});
const total = ref(0);
const hits = ref<SearchHit[]>([]);
const facets = reactive<Record<string, FacetValue[]>>({});
const authed = ref(true);
const loading = ref(false);

const pagination = reactive({
  page: 1,
  pageSize: 20,
  itemCount: 0,
  showSizePicker: true,
  pageSizes: [20, 50, 100],
  prefix: ({ itemCount }: { itemCount: number }) => `共 ${itemCount} 件`,
});

// ── 命中标红 ──────────────────────────────────────────────────────────────────
const HL = "color:#dc2626;font-weight:600";
const appliedKeyword = ref(""); // 检索时快照，结果标红用（不随输入框实时变）

function escapeHtml(s: string): string {
  return s.replace(/[&<>"]/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;" }[c] as string));
}

// ES 高亮 <em> → 红色（先转义防注入，再还原标记）
function hl(raw?: string, fallback = ""): string {
  const s = raw ?? fallback ?? "";
  const esc = escapeHtml(s);
  return esc.replace(/&lt;em&gt;/g, `<span style="${HL}">`).replace(/&lt;\/em&gt;/g, "</span>");
}

// 客户端按当前关键词在文本里标红（档号走 wildcard、ES 不给高亮，必须客户端标）
function markKw(text?: string): string {
  if (!text) return "—";
  const safe = escapeHtml(text);
  const t = appliedKeyword.value.trim();
  if (!t) return safe;
  const pat = t.replace(/[.*+?^${}()|[\]\\]/g, "\\$&");
  try {
    return safe.replace(new RegExp(`(${pat})`, "gi"), `<span style="${HL}">$1</span>`);
  } catch {
    return safe;
  }
}

// 命中渲染：ES 高亮优先（题名/责任者/原文），否则客户端按关键词标红
function cellHtml(esArr?: string[], raw?: string): string {
  return esArr?.length ? hl(esArr[0]) : markKw(raw);
}

const catMap = ref<Record<string, string>>({});
function catName(id?: string): string {
  return (id && catMap.value[id]) || "—";
}

// 题名单元格：命中标红；有原文才可点开
function tmCell(r: SearchHit) {
  return h("span", {
    class: r.has_source ? "text-[13px] cursor-pointer hover:underline" : "text-[13px]",
    style: "color: var(--semi-color-text-0)",
    innerHTML: cellHtml(r.highlight?.TM, r.TM),
    onClick: r.has_source ? () => openReader(r.id) : undefined,
  });
}

function dhCell(r: SearchHit) {
  return h("span", { class: "font-mono text-[12px]", style: "white-space: nowrap", innerHTML: markKw(r.DH || "—") });
}

function mjCell(r: SearchHit) {
  return r.MJ && r.MJ !== "无"
    ? h(NTag, { size: "tiny", type: "error", round: true }, { default: () => r.MJ })
    : h("span", { class: "text-xs", style: "color: var(--semi-color-text-3)" }, "无");
}

const RETENTION_LABEL: Record<string, string> = { permanent: "永久", long: "长期", short: "短期" };
function facetValueLabel(f: string, label: string): string {
  return f === "BGQX" ? (RETENTION_LABEL[label] ?? label) : label;
}

// ── 档案详情（拉全量字段，含门类扩展字段）────────────────────────────────────
const detailShow = ref(false);
const detailLoading = ref(false);
const detailRow = ref<SearchHit | null>(null);
const detail = ref<Archive | null>(null);

async function openDetail(r: SearchHit) {
  detailRow.value = r;
  detail.value = null;
  detailShow.value = true;
  detailLoading.value = true;
  try {
    const res = await ArchiveAPI.get(r.id);
    if (res.code === 0) detail.value = res.data;
  } finally {
    detailLoading.value = false;
  }
}

const detailFields = computed(() => {
  const d = detail.value;
  if (!d) return [];
  const base = [
    { label: "档号", value: d.DH, mono: true },
    { label: "题名", value: d.TM },
    { label: "全宗号", value: d.QZH },
    { label: "责任者", value: d.RZZ },
    { label: "年度", value: d.ND ? String(d.ND) : "" },
    { label: "文件日期", value: d.WJRQ },
    { label: "页数", value: d.YS ? String(d.YS) : "" },
    { label: "密级", value: d.MJ },
    { label: "保管期限", value: RETENTION_LABEL[d.BGQX] ?? d.BGQX },
    { label: "开放状态", value: d.KFZT ?? "未鉴定" },
    { label: "门类", value: catName(d.category_id) },
  ];
  const ext = Object.entries(d.ext_fields ?? {})
    .filter(([, v]) => v !== null && v !== "")
    .map(([k, v]) => ({ label: k, value: String(v), mono: false }));
  return [...base, ...ext];
});

function actionCell(r: SearchHit) {
  return h("div", { class: "flex items-center gap-1" }, [
    h(NButton, { size: "tiny", tertiary: true, onClick: () => openDetail(r) }, { default: () => "详情" }),
    h(NButton, {
      size: "tiny", tertiary: true, type: "primary",
      disabled: !r.has_source,
      title: r.has_source ? "查看原文" : "该档案暂无数字化原文",
      onClick: () => openReader(r.id),
    }, { default: () => "查看原文" }),
    h(NButton, { size: "tiny", tertiary: true, type: "primary", onClick: () => openInterpret(r) }, { default: () => "AI 解读" }),
  ]);
}

// 字段检索表头：结构化字段铺开
const fieldColumns: DataTableColumns<SearchHit> = [
  { title: "档号", key: "DH", width: 215, render: dhCell },
  { title: "题名", key: "TM", minWidth: 280, ellipsis: { tooltip: true }, render: tmCell },
  { title: "责任者", key: "RZZ", width: 120, render: (r) => h("span", { class: "text-[13px]", innerHTML: cellHtml(r.highlight?.RZZ, r.RZZ) }) },
  { title: "年度", key: "ND", width: 70, render: (r) => r.ND || "—" },
  { title: "全宗号", key: "QZH", width: 84, render: (r) => r.QZH || "—" },
  { title: "门类", key: "category_id", width: 130, ellipsis: { tooltip: true }, render: (r) => catName(r.category_id) },
  { title: "密级", key: "MJ", width: 76, render: mjCell },
  { title: "保管期限", key: "BGQX", width: 90, render: (r) => RETENTION_LABEL[r.BGQX ?? ""] ?? r.BGQX ?? "—" },
  { title: "操作", key: "actions", width: 200, fixed: "right" as const, render: actionCell },
];

// 全文检索表头：突出"命中内容（原文）"
const fulltextColumns: DataTableColumns<SearchHit> = [
  { title: "档号", key: "DH", width: 200, render: dhCell },
  { title: "题名", key: "TM", width: 240, ellipsis: { tooltip: true }, render: tmCell },
  {
    title: "原文（命中标红）", key: "_fulltext", minWidth: 420,
    render: (r) =>
      r.full_text
        ? h("div", {
            class: "text-[12.5px] leading-relaxed",
            style: "color: var(--semi-color-text-1); max-height: 132px; overflow-y: auto; white-space: pre-wrap",
            innerHTML: markKw(r.full_text),
          })
        : h("span", { class: "text-[12px]", style: "color: var(--semi-color-text-3)" }, "（该档案无数字化原文/OCR 全文）"),
  },
  { title: "年度", key: "ND", width: 70, render: (r) => r.ND || "—" },
  { title: "全宗号", key: "QZH", width: 84, render: (r) => r.QZH || "—" },
  { title: "密级", key: "MJ", width: 76, render: mjCell },
  { title: "操作", key: "actions", width: 200, fixed: "right" as const, render: actionCell },
];

const activeColumns = computed(() => {
  void appliedKeyword.value; // 依赖关键词：变了就给新数组，强制 NDataTable 重渲染标红单元格
  return mode.value === "fulltext" ? [...fulltextColumns] : [...fieldColumns];
});

// 列总宽超出容器时出横向滚动条（操作列固定右侧），避免表格挤压变形
const activeScrollX = computed(() => (mode.value === "fulltext" ? 1290 : 1230));

// ── 分面交互 ──────────────────────────────────────────────────────────────────
function toggleSection(f: string) { open[f] = !open[f]; }
function toggleExpand(f: string) { expanded[f] = !expanded[f]; }
function visibleFacet(f: string): FacetValue[] {
  const list = facets[f] || [];
  return expanded[f] ? list : list.slice(0, FACET_LIMIT);
}
function isSelected(field: string, value: string | number): boolean {
  return (selected[field] || []).some((v) => v === value);
}
function toggleFacet(field: string, value: string | number) {
  const arr = selected[field] || [];
  selected[field] = arr.some((v) => v === value) ? arr.filter((v) => v !== value) : [...arr, value];
  pagination.page = 1;
  search();
}
function clearFacets() {
  facetOrder.forEach((f) => (selected[f] = []));
  pagination.page = 1;
  search();
}

const activeChips = computed(() =>
  facetOrder.flatMap((field) =>
    (selected[field] || []).map((value) => {
      const bucket = (facets[field] || []).find((b) => b.value === value);
      return { key: `${field}:${value}`, field, value, label: bucket?.label ?? String(value) };
    }),
  ),
);

// ── 检索 ──────────────────────────────────────────────────────────────────────
function switchMode(m: SearchMode) {
  if (mode.value === m) return;
  mode.value = m;
  pagination.page = 1;
  search();
}
function runSearch() { pagination.page = 1; search(); }
function onPage(p: number) { pagination.page = p; search(); }
function onPageSize(s: number) { pagination.pageSize = s; pagination.page = 1; search(); }

async function search() {
  loading.value = true;
  appliedKeyword.value = keyword.value; // 快照，命中标红用
  try {
    const res = await SuperSearchAPI.search({
      keyword: keyword.value || undefined,
      mode: mode.value,
      QZH: selected.QZH as string[],
      ND: selected.ND as number[],
      RZZ: selected.RZZ as string[],
      MJ: selected.MJ as string[],
      BGQX: selected.BGQX as string[],
      category_id: selected.category_id as string[],
      page: pagination.page,
      page_size: pagination.pageSize,
    });
    const d = res.data;
    total.value = d.total;
    pagination.itemCount = d.total;
    hits.value = d.hits;
    authed.value = d.authed;
    Object.assign(facets, d.facets);
    // 门类 id→名 取自分面标签（已在后端补名），匿名也可用，避免额外鉴权请求
    (d.facets.category_id || []).forEach((b) => {
      catMap.value[String(b.value)] = b.label;
    });
  } finally {
    loading.value = false;
  }
}

function resetAll() {
  keyword.value = "";
  facetOrder.forEach((f) => (selected[f] = []));
  pagination.page = 1;
  search();
}

function openReader(id: string) {
  window.open(`/archive/reader?id=${id}`, "_blank", "noopener");
}

// ── AI 解读 ───────────────────────────────────────────────────────────────────
const interpretShow = ref(false);
const interpretId = ref<string | null>(null);
const interpretTitle = ref("");
function openInterpret(r: SearchHit) {
  interpretId.value = r.id;
  interpretTitle.value = `${r.DH || ""} ${r.TM}`.trim();
  interpretShow.value = true;
}

onMounted(() => {
  const q = route.query.keyword;
  const m = route.query.mode;
  if (typeof q === "string") keyword.value = q;
  if (m === "field" || m === "fulltext") mode.value = m;
  search();
});
</script>
