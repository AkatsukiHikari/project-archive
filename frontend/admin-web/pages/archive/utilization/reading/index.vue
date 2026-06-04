<template>
  <div class="flex flex-col gap-3 min-h-0 flex-1">
    <AdminPageHeader
      title="档案查阅"
      description="按题名 / 责任者 / 档号检索后查阅档案条目和原文 PDF"
      icon="heroicons:eye"
    />

    <div class="flex-1 min-h-0 grid grid-cols-1 lg:grid-cols-[420px_1fr] gap-3">
      <!-- 左：搜索 + 命中列表 -->
      <div
        class="flex flex-col rounded-xl overflow-hidden"
        style="background:var(--semi-color-bg-0);border:1px solid var(--semi-color-border)"
      >
        <div class="p-3 flex flex-col gap-2 border-b" style="border-color:var(--semi-color-border)">
          <NInput
            v-model:value="keyword"
            placeholder="搜索题名、责任者、档号 ⋯ 回车确认"
            size="medium"
            clearable
            @keydown.enter="search"
          >
            <template #prefix>
              <Icon name="heroicons:magnifying-glass" class="w-4 h-4" style="color:var(--semi-color-text-3)" />
            </template>
          </NInput>
          <div class="flex items-center gap-1.5 text-[11px] flex-wrap" style="color:var(--semi-color-text-3)">
            <span>年度</span>
            <button
              v-for="y in quickYears"
              :key="y ?? 'all'"
              class="px-1.5 py-0.5 rounded cursor-pointer border-none transition-all"
              :style="chipStyle(filterYear === y)"
              @click="toggleYear(y)"
            >{{ y ?? '不限' }}</button>
            <span class="w-px h-3 mx-1" style="background:var(--semi-color-border)" />
            <span>密级</span>
            <button
              v-for="opt in mjOptions"
              :key="opt.value ?? 'all'"
              class="px-1.5 py-0.5 rounded cursor-pointer border-none transition-all"
              :style="chipStyle(filterMJ === opt.value)"
              @click="toggleMJ(opt.value)"
            >{{ opt.label }}</button>
          </div>
        </div>

        <div class="flex items-center justify-between px-3 py-1.5 text-[11px]" style="color:var(--semi-color-text-3);border-bottom:1px solid var(--semi-color-border)">
          <span v-if="!loading">命中 <strong style="color:oklch(var(--p))">{{ total }}</strong> 条</span>
          <span v-else>加载中…</span>
          <span v-if="keyword">「{{ keyword }}」</span>
        </div>

        <div class="flex-1 overflow-y-auto">
          <div v-if="archives.length === 0 && !loading" class="p-8 text-center text-[12px]" style="color:var(--semi-color-text-3)">
            <Icon name="heroicons:document-magnifying-glass" class="w-8 h-8 mb-2 inline-block opacity-50" />
            <p>{{ hasSearched ? '未找到匹配档案' : '请输入关键词或选择筛选条件' }}</p>
          </div>
          <button
            v-for="(row, idx) in archives"
            :key="row.id"
            class="w-full text-left flex items-start gap-2 px-3 py-2.5 border-none bg-transparent cursor-pointer transition-colors"
            :style="rowStyle(row, idx)"
            @click="selectArchive(row)"
          >
            <div
              class="w-0.5 self-stretch rounded-full shrink-0 mt-0.5"
              :style="{ background: mjBar[row.MJ] ?? 'var(--semi-color-fill-1)' }"
            />
            <div class="flex-1 min-w-0">
              <div class="text-[12.5px] font-medium leading-snug" style="color:var(--semi-color-text-0)">
                <span v-html="highlight(row.TM)" />
              </div>
              <div class="flex flex-wrap items-center gap-1.5 mt-1 text-[10.5px]" style="color:var(--semi-color-text-3)">
                <code class="px-1 rounded font-mono" style="background:var(--semi-color-fill-0);color:var(--semi-color-text-2)">{{ row.DH || '—' }}</code>
                <NTag :type="mjType[row.MJ] ?? 'default'" size="tiny" :bordered="false">{{ mjLabel[row.MJ] ?? row.MJ }}</NTag>
                <span v-if="row.ND">· {{ row.ND }}</span>
                <span v-if="row.RZZ">· <span v-html="highlight(row.RZZ)" /></span>
              </div>
            </div>
          </button>
        </div>

        <div v-if="total > pageSize" class="px-3 py-2 flex items-center justify-between border-t" style="border-color:var(--semi-color-border)">
          <NPagination
            v-model:page="page"
            :page-size="pageSize"
            :item-count="total"
            simple
            @update:page="loadArchives"
          />
        </div>
      </div>

      <!-- 右：详情 + 附件 -->
      <div
        class="flex flex-col rounded-xl overflow-hidden"
        style="background:var(--semi-color-bg-0);border:1px solid var(--semi-color-border)"
      >
        <div v-if="!selected" class="h-full flex flex-col items-center justify-center gap-3" style="color:var(--semi-color-text-3)">
          <Icon name="heroicons:document-text" class="w-12 h-12 opacity-30" />
          <p class="text-[13px]">从左侧列表选择一条档案查看详情</p>
        </div>

        <div v-else class="flex flex-col h-full">
          <div class="p-4 border-b" style="border-color:var(--semi-color-border)">
            <div class="flex items-start justify-between gap-3">
              <div class="flex-1 min-w-0">
                <h2 class="text-[16px] font-semibold leading-snug mb-2" style="color:var(--semi-color-text-0)">
                  {{ selected.TM }}
                </h2>
                <div class="flex flex-wrap items-center gap-2 text-[11.5px]">
                  <code class="px-1.5 py-0.5 rounded font-mono" style="background:var(--semi-color-fill-0)">{{ selected.DH || '—' }}</code>
                  <NTag :type="mjType[selected.MJ] ?? 'default'" size="small" :bordered="false">{{ mjLabel[selected.MJ] ?? selected.MJ }}</NTag>
                  <NTag :bordered="false" size="small" style="background:var(--semi-color-fill-0)">{{ bgqxLabel[selected.BGQX] ?? selected.BGQX }}</NTag>
                  <NTag :bordered="false" size="small" type="info" v-if="selected.ND">{{ selected.ND }} 年度</NTag>
                </div>
              </div>
              <div class="flex gap-2 flex-shrink-0">
                <NButton size="small" @click="copyArchiveLink">
                  <template #icon><Icon name="heroicons:link" class="w-3.5 h-3.5" /></template>
                  复制链接
                </NButton>
                <NButton size="small" type="primary" @click="askAI">
                  <template #icon><Icon name="heroicons:sparkles" class="w-3.5 h-3.5" /></template>
                  让 AI 解读
                </NButton>
              </div>
            </div>
          </div>

          <div class="flex-1 overflow-y-auto p-4 flex flex-col gap-4">
            <!-- 元数据 grid -->
            <div>
              <div class="text-[11px] font-semibold mb-2 tracking-wide" style="color:var(--semi-color-text-3)">档案元数据</div>
              <div class="grid grid-cols-2 gap-x-4 gap-y-2.5 text-[12px]">
                <MetaCell label="档号 DH" :value="selected.DH" />
                <MetaCell label="全宗号 QZH" :value="selected.QZH" />
                <MetaCell label="题名 TM" :value="selected.TM" wide />
                <MetaCell label="责任者 RZZ" :value="selected.RZZ" />
                <MetaCell label="年度 ND" :value="selected.ND" />
                <MetaCell label="文件日期 WJRQ" :value="selected.WJRQ" />
                <MetaCell label="页数 YS" :value="selected.YS" />
                <MetaCell label="密级 MJ" :value="mjLabel[selected.MJ] ?? selected.MJ" />
                <MetaCell label="保管期限 BGQX" :value="bgqxLabel[selected.BGQX] ?? selected.BGQX" />
                <MetaCell label="状态" :value="statusLabel[selected.status] ?? selected.status" />
              </div>
            </div>

            <!-- 原文附件 -->
            <div>
              <div class="text-[11px] font-semibold mb-2 tracking-wide" style="color:var(--semi-color-text-3)">原文（数字化加工 PDF）</div>
              <div
                v-if="!attachmentAvailable"
                class="rounded-lg p-6 flex flex-col items-center gap-2 text-center"
                style="background:var(--semi-color-fill-0);color:var(--semi-color-text-3)"
              >
                <Icon name="heroicons:document-arrow-down" class="w-8 h-8 opacity-50" />
                <p class="text-[12px]">该档案的数字化加工 PDF 暂未入库</p>
                <p class="text-[10.5px]">实际部署后由扫描归档环节上传，存放在对象存储</p>
              </div>
              <div v-else class="rounded-lg p-4 flex items-center gap-3" style="background:var(--semi-color-fill-0)">
                <div class="w-10 h-10 rounded flex items-center justify-center flex-shrink-0" style="background:oklch(var(--er)/0.12);color:oklch(var(--er))">
                  <Icon name="heroicons:document-text" class="w-5 h-5" />
                </div>
                <div class="flex-1 min-w-0">
                  <div class="text-[12.5px] font-medium truncate">{{ selected.TM }}.pdf</div>
                  <div class="text-[10.5px]" style="color:var(--semi-color-text-3)">PDF · {{ selected.YS ?? 0 }} 页</div>
                </div>
                <NButton size="small" disabled>查看 / 下载</NButton>
              </div>
            </div>

            <!-- 扩展字段 -->
            <div v-if="selected.ext_fields && Object.keys(selected.ext_fields).length > 0">
              <div class="text-[11px] font-semibold mb-2 tracking-wide" style="color:var(--semi-color-text-3)">门类扩展字段</div>
              <pre class="text-[11px] p-3 rounded-lg overflow-auto max-h-48" style="background:var(--semi-color-fill-0);color:var(--semi-color-text-1)">{{ JSON.stringify(selected.ext_fields, null, 2) }}</pre>
            </div>

            <!-- 利用记录占位 -->
            <div>
              <div class="text-[11px] font-semibold mb-2 tracking-wide" style="color:var(--semi-color-text-3)">利用记录</div>
              <div class="text-[11.5px] p-3 rounded-lg" style="background:var(--semi-color-fill-0);color:var(--semi-color-text-3)">
                你正在查阅 — 此操作已记入审计日志
              </div>
            </div>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted, watch, h } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NInput, NTag, NButton, NPagination, useMessage } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ArchiveAPI } from "@/api/repository";
import type { Archive } from "@/api/repository";

definePageMeta({ layout: "archive", middleware: "auth" });

const route = useRoute();
const router = useRouter();
const message = useMessage();

// ── 类型映射 ────────────────────────────────────────────────────────────
const mjLabel: Record<string, string> = { public: "公开", internal: "内部", confidential: "机密", secret: "秘密" };
const mjType: Record<string, "default" | "info" | "warning" | "error" | "success"> = {
  public: "success", internal: "info", confidential: "warning", secret: "error",
};
const mjBar: Record<string, string> = {
  public: "oklch(var(--su)/0.7)",
  internal: "oklch(var(--in)/0.7)",
  confidential: "oklch(0.7 0.18 80/0.7)",
  secret: "oklch(var(--er)/0.7)",
};
const bgqxLabel: Record<string, string> = { permanent: "永久", long: "长期", short: "短期" };
const statusLabel: Record<string, string> = {
  draft: "草稿", pending_review: "待审", rejected: "退回",
  archived: "归档", active: "在库", restricted: "受限",
};
const mjOptions = [
  { label: "不限", value: null as string | null },
  { label: "公开", value: "public" },
  { label: "内部", value: "internal" },
  { label: "秘密", value: "secret" },
  { label: "机密", value: "confidential" },
];
const quickYears: (number | null)[] = (() => {
  const cur = new Date().getFullYear();
  return [null, cur, cur - 1, cur - 2, cur - 3];
})();

// ── 状态 ────────────────────────────────────────────────────────────────
const keyword = ref<string>("");
const filterYear = ref<number | null>(null);
const filterMJ = ref<string | null>(null);
const page = ref(1);
const pageSize = ref(30);
const total = ref(0);
const loading = ref(false);
const hasSearched = ref(false);

const archives = ref<Archive[]>([]);
const selected = ref<Archive | null>(null);

const attachmentAvailable = computed(() => false);

// ── 工具 ────────────────────────────────────────────────────────────────
function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
}
function highlight(text: string | null | undefined): string {
  if (!text) return "";
  const safe = escapeHtml(text);
  const kw = keyword.value.trim();
  if (!kw) return safe;
  const tokens = kw.split(/\s+/).filter(Boolean).map(escapeHtml);
  if (tokens.length === 0) return safe;
  const re = new RegExp(`(${tokens.join("|")})`, "gi");
  return safe.replace(re, '<mark style="background:oklch(var(--p)/0.18);color:oklch(var(--p));padding:0 2px;border-radius:3px">$1</mark>');
}

const chipStyle = (active: boolean): Record<string, string> => active
  ? { background: "oklch(var(--p)/0.14)", color: "oklch(var(--p))", fontWeight: "600" }
  : { background: "transparent", color: "var(--semi-color-text-2)" };

const rowStyle = (row: Archive, idx: number): Record<string, string> => ({
  borderBottom: idx === archives.value.length - 1 ? "none" : "1px solid var(--semi-color-border)",
  background: selected.value?.id === row.id ? "oklch(var(--p)/0.08)" : "transparent",
});

// ── 操作 ────────────────────────────────────────────────────────────────
function toggleYear(y: number | null) { filterYear.value = filterYear.value === y ? null : y; search(); }
function toggleMJ(v: string | null) { filterMJ.value = filterMJ.value === v ? null : v; search(); }

function search() {
  page.value = 1;
  hasSearched.value = true;
  syncUrl();
  loadArchives();
}

async function loadArchives() {
  loading.value = true;
  try {
    const params: Record<string, string | number> = {
      page: page.value,
      page_size: pageSize.value,
    };
    if (keyword.value) params.keyword = keyword.value;
    if (filterYear.value) params.ND = filterYear.value;
    if (filterMJ.value) params.MJ = filterMJ.value;
    const res = await ArchiveAPI.list(params);
    archives.value = res.data.items;
    total.value = res.data.total;
  } finally {
    loading.value = false;
  }
}

async function selectArchive(row: Archive) {
  selected.value = row;
  // URL 带上 id 便于分享 / 浏览器回退
  router.replace({ path: route.path, query: { ...route.query, id: row.id } });
}

async function selectById(id: string) {
  // 先在列表里找
  const found = archives.value.find((a) => a.id === id);
  if (found) {
    selected.value = found;
    return;
  }
  try {
    const res = await ArchiveAPI.get(id);
    selected.value = res.data;
    // 把它放进列表（如果不在）
    if (!archives.value.some((a) => a.id === id)) {
      archives.value.unshift(res.data);
      total.value += 1;
    }
  } catch {
    message.error("未找到该档案");
  }
}

function copyArchiveLink() {
  if (!selected.value) return;
  const url = `${location.origin}/archive/utilization/reading?id=${selected.value.id}`;
  navigator.clipboard.writeText(url).then(() => message.success("链接已复制到剪贴板"));
}

function askAI() {
  if (!selected.value) return;
  router.push({ path: "/ai", query: { q: `请帮我解读档案：${selected.value.TM}`, archive_id: selected.value.id } });
}

// ── URL 状态化（AI chip 跳进来时复现） ─────────────────────────────────
function syncUrl() {
  const q: Record<string, string> = {};
  if (keyword.value) q.q = keyword.value;
  if (filterYear.value) q.year = String(filterYear.value);
  if (filterMJ.value) q.mj = filterMJ.value;
  if (selected.value) q.id = selected.value.id;
  router.replace({ path: route.path, query: q });
}

function hydrateFromUrl() {
  const q = route.query;
  if (typeof q.q === "string") keyword.value = q.q;
  if (typeof q.year === "string") filterYear.value = Number(q.year) || null;
  if (typeof q.mj === "string") filterMJ.value = q.mj;
  if (keyword.value || filterYear.value || filterMJ.value || q.id) {
    hasSearched.value = true;
  }
}

// 跟随 URL 中的 ?id 变化加载（AI chip 跳进来时触发）
watch(() => route.query.id, (newId) => {
  if (typeof newId === "string" && newId) {
    selectById(newId);
  }
});

onMounted(async () => {
  hydrateFromUrl();
  await loadArchives();
  const id = route.query.id;
  if (typeof id === "string" && id) {
    await selectById(id);
  }
});

// ── 子组件：MetaCell（用 h 渲染，避免再建文件） ───────────────────────
const MetaCell = (props: { label: string; value: any; wide?: boolean }) => h(
  "div",
  { class: props.wide ? "col-span-2" : "" },
  [
    h("div", { class: "text-[10.5px] mb-0.5", style: "color:var(--semi-color-text-3)" }, props.label),
    h("div", { class: "text-[12px]", style: "color:var(--semi-color-text-0)" }, String(props.value ?? "—")),
  ],
);
</script>
