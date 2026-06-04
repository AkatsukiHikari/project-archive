<template>
  <div class="flex flex-col gap-4 min-h-0 flex-1">
    <AdminPageHeader
      title="档案检索 / 著录"
      description="按题名、责任者、档号、年度、密级一键检索；点击命中行可查看完整元数据"
      icon="heroicons:magnifying-glass-circle"
    />

    <!-- ════════════════════════════════════════════════════════
         主搜索区
    ════════════════════════════════════════════════════════ -->
    <div
      class="rounded-xl p-4 flex flex-col gap-3 flex-shrink-0"
      style="background:var(--semi-color-bg-0);border:1px solid var(--semi-color-border)"
    >
      <div class="flex items-stretch gap-2">
        <div class="flex-1">
          <NInput
            v-model:value="filter.keyword"
            placeholder="搜索题名、责任者、档号 ⋯ 例如「2024 财务凭证」「干部任免」"
            size="large"
            clearable
            @keydown.enter="search"
          >
            <template #prefix>
              <Icon name="heroicons:magnifying-glass" class="w-4 h-4" style="color:var(--semi-color-text-3)" />
            </template>
          </NInput>
        </div>
        <NButton type="primary" size="large" :loading="loading" @click="search">
          <template #icon><Icon name="heroicons:magnifying-glass" class="w-4 h-4" /></template>
          搜索
        </NButton>
        <NButton size="large" @click="resetFilter">重置</NButton>
        <NButton size="large" :disabled="!filter.fonds_id" @click="openModal(null)">
          <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
          新增
        </NButton>
      </div>

      <!-- 快捷过滤 chip 行 -->
      <div class="flex flex-wrap items-center gap-x-4 gap-y-2">
        <div class="flex items-center gap-1.5">
          <span class="text-[11.5px] shrink-0" style="color:var(--semi-color-text-3)">年度</span>
          <button
            v-for="y in quickYears"
            :key="y ?? 'all'"
            class="px-2 py-0.5 rounded-full text-[11.5px] cursor-pointer border-none transition-all"
            :style="chipStyle(filter.ND === y)"
            @click="toggleYear(y)"
          >
            {{ y ?? '不限' }}
          </button>
        </div>

        <span class="w-px h-4 shrink-0" style="background:var(--semi-color-border)" />

        <div class="flex items-center gap-1.5">
          <span class="text-[11.5px] shrink-0" style="color:var(--semi-color-text-3)">密级</span>
          <button
            v-for="opt in securityOptions"
            :key="opt.value ?? 'all'"
            class="px-2 py-0.5 rounded-full text-[11.5px] cursor-pointer border-none transition-all"
            :style="chipStyle(filter.MJ === opt.value)"
            @click="toggleMJ(opt.value)"
          >
            {{ opt.label }}
          </button>
        </div>

        <span class="w-px h-4 shrink-0" style="background:var(--semi-color-border)" />

        <div class="flex items-center gap-1.5">
          <span class="text-[11.5px] shrink-0" style="color:var(--semi-color-text-3)">全宗</span>
          <NSelect
            v-model:value="filter.fonds_id"
            :options="fondsOptions"
            placeholder="全部"
            size="tiny"
            style="width: 180px"
            clearable
            @update:value="onFondsChange"
          />
        </div>
        <div class="flex items-center gap-1.5">
          <span class="text-[11.5px] shrink-0" style="color:var(--semi-color-text-3)">门类</span>
          <NSelect
            v-model:value="filter.category_id"
            :options="categoryOptions"
            placeholder="全部"
            size="tiny"
            style="width: 140px"
            clearable
            @update:value="search"
          />
        </div>
        <div v-if="filter.fonds_id" class="flex items-center gap-1.5">
          <span class="text-[11.5px] shrink-0" style="color:var(--semi-color-text-3)">目录</span>
          <NSelect
            v-model:value="filter.catalog_id"
            :options="catalogOptions"
            placeholder="全部"
            size="tiny"
            style="width: 200px"
            clearable
            @update:value="search"
          />
        </div>
      </div>
    </div>

    <!-- 命中统计行 -->
    <div
      v-if="!loading && total > 0"
      class="flex items-center gap-3 px-1 text-[12px] flex-shrink-0"
      style="color:var(--semi-color-text-2)"
    >
      <span class="font-medium" style="color:var(--semi-color-text-0)">
        命中 <span class="tabular-nums" style="color:oklch(var(--p));font-weight:600">{{ total }}</span> 条
      </span>
      <span v-if="hitStats.fonds > 0">· 跨 {{ hitStats.fonds }} 个全宗</span>
      <span v-if="hitStats.years">· {{ hitStats.years }}</span>
      <span v-if="filter.keyword" class="ml-auto" style="color:var(--semi-color-text-3)">
        关键词：「{{ filter.keyword }}」
      </span>
    </div>

    <!-- 命中列表 / 空态 -->
    <div
      class="flex-1 min-h-[300px] rounded-xl overflow-hidden"
      style="background:var(--semi-color-bg-0);border:1px solid var(--semi-color-border)"
    >
      <div
        v-if="!loading && archiveList.length === 0 && !hasSearched"
        class="h-full flex flex-col items-center justify-center gap-5 px-8"
      >
        <div class="w-16 h-16 rounded-2xl flex items-center justify-center" style="background:oklch(var(--p)/0.1)">
          <Icon name="heroicons:archive-box" class="w-8 h-8" style="color:oklch(var(--p))" />
        </div>
        <div class="text-center">
          <p class="text-[15px] font-semibold mb-1" style="color:var(--semi-color-text-0)">在档案库中检索</p>
          <p class="text-[12px]" style="color:var(--semi-color-text-2)">支持题名 / 责任者 / 档号关键词，回车即搜</p>
        </div>
        <div class="flex flex-wrap gap-2 justify-center max-w-2xl">
          <button
            v-for="ex in EXAMPLE_QUERIES"
            :key="ex"
            class="text-[12px] px-3 py-1.5 rounded-full border cursor-pointer transition-colors hover:bg-[var(--semi-color-fill-0)]"
            style="border-color:var(--semi-color-border);color:var(--semi-color-text-1)"
            @click="runExample(ex)"
          >{{ ex }}</button>
        </div>
      </div>

      <div
        v-else-if="!loading && archiveList.length === 0 && hasSearched"
        class="h-full flex flex-col items-center justify-center gap-3"
      >
        <Icon name="heroicons:face-frown" class="w-10 h-10" style="color:var(--semi-color-text-3)" />
        <p class="text-[13px]" style="color:var(--semi-color-text-2)">未找到匹配的档案</p>
        <p class="text-[11.5px]" style="color:var(--semi-color-text-3)">试试换个关键词，或放宽筛选条件</p>
      </div>

      <div v-else class="h-full overflow-y-auto">
        <div
          v-if="loading && archiveList.length === 0"
          class="h-full flex items-center justify-center text-[12px]"
          style="color:var(--semi-color-text-3)"
        >加载中…</div>
        <div v-else>
          <button
            v-for="(row, idx) in archiveList"
            :key="row.id"
            class="w-full text-left flex items-start gap-3 px-4 py-3 border-none bg-transparent cursor-pointer transition-colors"
            :style="rowStyle(row, idx)"
            @click="openDetail(row)"
            @mouseenter="(e) => activateRow(e)"
            @mouseleave="(e) => deactivateRow(e, row)"
          >
            <div
              class="w-1 self-stretch rounded-full shrink-0 mt-0.5"
              :style="{ background: securityBar[row.MJ] ?? 'var(--semi-color-fill-1)' }"
            />
            <div class="flex-1 min-w-0">
              <div class="flex items-center gap-2 flex-wrap">
                <span class="text-[13px] font-medium" style="color:var(--semi-color-text-0)">
                  <span v-html="highlight(row.TM)" />
                </span>
                <NTag :type="securityType[row.MJ] ?? 'default'" size="tiny" :bordered="false">
                  {{ securityLabel[row.MJ] ?? row.MJ }}
                </NTag>
                <NTag size="tiny" :bordered="false" style="background:var(--semi-color-fill-0)">
                  {{ retentionLabel[row.BGQX] ?? row.BGQX }}
                </NTag>
              </div>
              <div class="flex items-center gap-2 mt-1 text-[11.5px]" style="color:var(--semi-color-text-3)">
                <code class="px-1 rounded font-mono" style="background:var(--semi-color-fill-0);color:var(--semi-color-text-1)">
                  {{ row.DH || '—' }}
                </code>
                <span v-if="row.RZZ">· <span v-html="highlight(row.RZZ)" /></span>
                <span v-if="row.ND">· {{ row.ND }} 年度</span>
                <span v-if="row.WJRQ">· 文件日期 {{ row.WJRQ }}</span>
                <span>· 全宗 {{ row.QZH }}</span>
              </div>
            </div>
            <div class="flex items-center gap-2 shrink-0">
              <span class="text-[11px] px-1.5 py-0.5 rounded" :style="statusStyleFor(row.status)">
                {{ statusLabel[row.status] ?? row.status }}
              </span>
              <Icon name="heroicons:chevron-right" class="w-4 h-4" style="color:var(--semi-color-text-3)" />
            </div>
          </button>
        </div>
      </div>
    </div>

    <div v-if="total > 0" class="flex items-center justify-between flex-shrink-0">
      <span class="text-[11.5px]" style="color:var(--semi-color-text-3)">
        第 {{ filter.page }} / {{ Math.max(1, Math.ceil(total / filter.page_size)) }} 页
      </span>
      <NPagination
        v-model:page="filter.page"
        v-model:page-size="filter.page_size"
        :item-count="total"
        :page-sizes="[20, 50, 100]"
        show-size-picker
        @update:page="loadArchives"
        @update:page-size="loadArchives"
      />
    </div>

    <!-- ════════════════════════════════════════════════════════
         详情抽屉
    ════════════════════════════════════════════════════════ -->
    <NDrawer v-model:show="detailVisible" :width="520" placement="right">
      <NDrawerContent v-if="detailRow" :title="detailRow.TM" closable>
        <div class="flex flex-col gap-4">
          <div class="flex items-center gap-2 flex-wrap">
            <NTag :type="securityType[detailRow.MJ] ?? 'default'" :bordered="false">
              {{ securityLabel[detailRow.MJ] ?? detailRow.MJ }}
            </NTag>
            <NTag :bordered="false">{{ retentionLabel[detailRow.BGQX] ?? detailRow.BGQX }}</NTag>
            <NTag :bordered="false">{{ statusLabel[detailRow.status] ?? detailRow.status }}</NTag>
            <NTag :bordered="false" type="info">{{ detailRow.ND ?? '—' }} 年度</NTag>
          </div>

          <div class="grid grid-cols-2 gap-x-4 gap-y-3 text-[12px]">
            <div>
              <div style="color:var(--semi-color-text-3)" class="text-[10.5px]">档号 DH</div>
              <code class="font-mono">{{ detailRow.DH || '—' }}</code>
            </div>
            <div>
              <div style="color:var(--semi-color-text-3)" class="text-[10.5px]">全宗号 QZH</div>
              <span>{{ detailRow.QZH }}</span>
            </div>
            <div>
              <div style="color:var(--semi-color-text-3)" class="text-[10.5px]">责任者 RZZ</div>
              <span>{{ detailRow.RZZ || '—' }}</span>
            </div>
            <div>
              <div style="color:var(--semi-color-text-3)" class="text-[10.5px]">文件日期 WJRQ</div>
              <span>{{ detailRow.WJRQ || '—' }}</span>
            </div>
            <div>
              <div style="color:var(--semi-color-text-3)" class="text-[10.5px]">页数 YS</div>
              <span>{{ detailRow.YS ?? '—' }}</span>
            </div>
            <div>
              <div style="color:var(--semi-color-text-3)" class="text-[10.5px]">门类</div>
              <span>{{ categoryNameById[detailRow.category_id] ?? '—' }}</span>
            </div>
          </div>

          <div v-if="detailRow.ext_fields && Object.keys(detailRow.ext_fields).length > 0">
            <div class="text-[10.5px] mb-1.5" style="color:var(--semi-color-text-3)">门类扩展字段</div>
            <pre class="text-[11px] p-3 rounded-lg overflow-auto max-h-48" style="background:var(--semi-color-fill-0);color:var(--semi-color-text-1)">{{ JSON.stringify(detailRow.ext_fields, null, 2) }}</pre>
          </div>

          <div class="flex gap-2 mt-2">
            <NButton type="primary" @click="() => { openModal(detailRow!); detailVisible = false; }">
              <template #icon><Icon name="heroicons:pencil-square" class="w-4 h-4" /></template>
              编辑
            </NButton>
            <NButton type="error" ghost @click="() => confirmDelete(detailRow!)">
              <template #icon><Icon name="heroicons:trash" class="w-4 h-4" /></template>
              删除
            </NButton>
            <div class="ml-auto flex items-center gap-1.5 text-[11px]" style="color:var(--semi-color-text-3)">
              <Icon name="heroicons:sparkles" class="w-3.5 h-3.5" style="color:oklch(var(--p))" />
              <button
                class="cursor-pointer border-none bg-transparent p-0 underline"
                style="color:oklch(var(--p))"
                @click="askAI(detailRow)"
              >让 AI 帮我解读</button>
            </div>
          </div>
        </div>
      </NDrawerContent>
    </NDrawer>

    <!-- 编辑弹窗 -->
    <CrudModal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑档案' : '新增档案'"
      :loading="saving"
      :width="600"
      @confirm="submitForm"
    >
      <NForm ref="formRef" :model="formData" :rules="rules" label-placement="left" :label-width="90">
        <NFormItem path="fonds_id" label="全宗">
          <NSelect v-model:value="formData.fonds_id" :options="fondsOptions" :disabled="isEdit" placeholder="选择全宗" @update:value="onFormFondsChange" />
        </NFormItem>
        <NFormItem path="catalog_id" label="目录">
          <NSelect v-model:value="formData.catalog_id" :options="formCatalogOptions" placeholder="选择目录" :disabled="!formData.fonds_id || isEdit" />
        </NFormItem>
        <NFormItem path="category_id" label="门类">
          <NSelect v-model:value="formData.category_id" :options="categoryOptions" placeholder="选择门类" />
        </NFormItem>
        <NFormItem path="TM" label="题名">
          <NInput v-model:value="formData.TM" placeholder="档案题名（必填）" />
        </NFormItem>
        <NFormItem path="QZH" label="全宗号">
          <NInput v-model:value="formData.QZH" placeholder="如 J001" />
        </NFormItem>
        <div class="grid grid-cols-2 gap-x-4">
          <NFormItem path="RZZ" label="责任者">
            <NInput v-model:value="formData.RZZ" placeholder="可选" />
          </NFormItem>
          <NFormItem path="ND" label="年度">
            <NInputNumber v-model:value="formData.ND" placeholder="年度" class="w-full" />
          </NFormItem>
          <NFormItem path="MJ" label="密级">
            <NSelect v-model:value="formData.MJ" :options="securityOptionsForm" class="w-full" />
          </NFormItem>
          <NFormItem path="BGQX" label="保管期限">
            <NSelect v-model:value="formData.BGQX" :options="retentionOptions" class="w-full" />
          </NFormItem>
          <NFormItem path="WJRQ" label="文件日期">
            <NInput v-model:value="formData.WJRQ" placeholder="YYYY-MM-DD" />
          </NFormItem>
          <NFormItem path="YS" label="页数">
            <NInputNumber v-model:value="formData.YS" placeholder="可选" class="w-full" />
          </NFormItem>
        </div>
        <NFormItem label="档号">
          <NInput v-model:value="formData.DH" placeholder="留空则自动生成（需配置档号规则）" />
        </NFormItem>
      </NForm>
    </CrudModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted, reactive, watch } from "vue";
import { useRoute, useRouter } from "vue-router";
import {
  NButton, NInput, NInputNumber, NSelect, NForm, NFormItem, NTag,
  NDrawer, NDrawerContent, NPagination,
  useMessage, useDialog,
} from "naive-ui";
import type { FormInst } from "naive-ui";
import { FondsAPI, CatalogAPI, CategoryAPI, ArchiveAPI } from "@/api/repository";
import type { Fonds, Catalog, ArchiveCategory, Archive, ArchiveCreate, ArchiveUpdate } from "@/api/repository";
import { AdminPageHeader } from "@/components/admin";
import { CrudModal } from "@/components/ui";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();
const router = useRouter();
const route = useRoute();

// ── 引用数据 ────────────────────────────────────────────────────────────────
const fondsList = ref<Fonds[]>([]);
const catalogList = ref<Catalog[]>([]);
const categoryList = ref<ArchiveCategory[]>([]);
const formCatalogs = ref<Catalog[]>([]);

const fondsOptions = computed(() =>
  fondsList.value.map((f) => ({ label: `${f.fonds_code} - ${f.short_name || f.name}`, value: f.id })),
);
const catalogOptions = computed(() =>
  catalogList.value.map((c) => ({ label: `${c.catalog_no} ${c.name}`, value: c.id })),
);
const formCatalogOptions = computed(() =>
  formCatalogs.value.map((c) => ({ label: `${c.catalog_no} ${c.name}`, value: c.id })),
);
const categoryOptions = computed(() =>
  categoryList.value.map((c) => ({ label: `${c.code} - ${c.name}`, value: c.id })),
);
const categoryNameById = computed<Record<string, string>>(() =>
  Object.fromEntries(categoryList.value.map((c) => [c.id, `${c.code} - ${c.name}`])),
);

const securityOptions = [
  { label: "不限", value: null as string | null },
  { label: "公开", value: "public" },
  { label: "内部", value: "internal" },
  { label: "秘密", value: "secret" },
  { label: "机密", value: "confidential" },
];
const securityOptionsForm = [
  { label: "公开", value: "public" },
  { label: "内部", value: "internal" },
  { label: "秘密", value: "secret" },
  { label: "机密", value: "confidential" },
];
const retentionOptions = [
  { label: "永久", value: "permanent" },
  { label: "长期", value: "long" },
  { label: "短期", value: "short" },
];
const securityLabel: Record<string, string> = {
  public: "公开", internal: "内部", confidential: "机密", secret: "秘密",
};
const securityType: Record<string, "default" | "info" | "warning" | "error" | "success"> = {
  public: "success", internal: "info", confidential: "warning", secret: "error",
};
const securityBar: Record<string, string> = {
  public: "oklch(var(--su)/0.7)",
  internal: "oklch(var(--in)/0.7)",
  confidential: "oklch(0.7 0.18 80/0.7)",
  secret: "oklch(var(--er)/0.7)",
};
const retentionLabel: Record<string, string> = {
  permanent: "永久", long: "长期", short: "短期",
};
const statusLabel: Record<string, string> = {
  draft: "草稿", pending_review: "待审", rejected: "退回",
  archived: "归档", active: "在库", restricted: "受限",
};
const statusStyleFor = (s: string): Record<string, string> => {
  switch (s) {
    case "archived":
    case "active":
      return { background: "oklch(var(--su)/0.12)", color: "oklch(var(--su))" };
    case "pending_review":
      return { background: "oklch(0.95 0.05 80)", color: "oklch(0.5 0.2 80)" };
    case "rejected":
      return { background: "oklch(var(--er)/0.12)", color: "oklch(var(--er))" };
    default:
      return { background: "var(--semi-color-fill-0)", color: "var(--semi-color-text-2)" };
  }
};

const EXAMPLE_QUERIES = [
  "2024 财务凭证",
  "干部任免",
  "档案信息化",
  "数字化建设",
  "永久保管",
  "审计报告",
];

const quickYears: (number | null)[] = (() => {
  const cur = new Date().getFullYear();
  return [null, cur, cur - 1, cur - 2, cur - 3, cur - 4];
})();

// ── 状态 ───────────────────────────────────────────────────────────────────
const filter = reactive({
  fonds_id: null as string | null,
  catalog_id: null as string | null,
  category_id: null as string | null,
  ND: null as number | null,
  keyword: "",
  MJ: null as string | null,
  status: null as string | null,
  page: 1,
  page_size: 20,
});

const archiveList = ref<Archive[]>([]);
const total = ref(0);
const loading = ref(false);
const hasSearched = ref(false);
const highlightId = ref<string | null>(null);

const detailVisible = ref(false);
const detailRow = ref<Archive | null>(null);

const hitStats = computed(() => {
  if (archiveList.value.length === 0) return { fonds: 0, years: "" };
  const fondsSet = new Set(archiveList.value.map((a) => a.QZH));
  const years = archiveList.value
    .map((a) => a.ND)
    .filter((y): y is number => typeof y === "number");
  if (years.length === 0) return { fonds: fondsSet.size, years: "" };
  const min = Math.min(...years);
  const max = Math.max(...years);
  return {
    fonds: fondsSet.size,
    years: min === max ? `${min} 年` : `${min} – ${max} 年`,
  };
});

// ── 高亮 ───────────────────────────────────────────────────────────────────
function escapeHtml(s: string): string {
  return s.replace(/[&<>"']/g, (c) => ({ "&": "&amp;", "<": "&lt;", ">": "&gt;", '"': "&quot;", "'": "&#39;" }[c]!));
}
function highlight(text: string | null | undefined): string {
  if (!text) return "";
  const safe = escapeHtml(text);
  const kw = filter.keyword.trim();
  if (!kw) return safe;
  const tokens = kw.split(/\s+/).filter((t) => t.length > 0).map(escapeHtml);
  if (tokens.length === 0) return safe;
  const re = new RegExp(`(${tokens.join("|")})`, "gi");
  return safe.replace(re, '<mark style="background:oklch(var(--p)/0.18);color:oklch(var(--p));padding:0 2px;border-radius:3px">$1</mark>');
}

// ── 行交互 ─────────────────────────────────────────────────────────────────
const chipStyle = (active: boolean): Record<string, string> => active
  ? { background: "oklch(var(--p)/0.14)", color: "oklch(var(--p))", fontWeight: "600", boxShadow: "0 0 0 1px oklch(var(--p)/0.3) inset" }
  : { background: "var(--semi-color-fill-0)", color: "var(--semi-color-text-2)" };

function rowStyle(row: Archive, idx: number): Record<string, string> {
  const isHighlighted = row.id === highlightId.value;
  return {
    borderBottom: idx === archiveList.value.length - 1 ? "none" : "1px solid var(--semi-color-border)",
    background: isHighlighted ? "oklch(var(--p)/0.06)" : "transparent",
  };
}

function activateRow(e: Event) {
  const el = e.currentTarget as HTMLElement;
  el.style.background = "var(--semi-color-fill-0)";
}
function deactivateRow(e: Event, row: Archive) {
  const el = e.currentTarget as HTMLElement;
  el.style.background = row.id === highlightId.value ? "oklch(var(--p)/0.06)" : "transparent";
}

// ── 操作 ───────────────────────────────────────────────────────────────────
async function onFondsChange(id: string | null) {
  filter.catalog_id = null;
  catalogList.value = [];
  if (id) {
    const res = await CatalogAPI.list(id);
    catalogList.value = res.data;
  }
  search();
}

function toggleYear(y: number | null) {
  filter.ND = filter.ND === y ? null : y;
  search();
}
function toggleMJ(v: string | null) {
  filter.MJ = filter.MJ === v ? null : v;
  search();
}

function resetFilter() {
  Object.assign(filter, {
    fonds_id: null, catalog_id: null, category_id: null,
    ND: null, keyword: "", MJ: null, status: null, page: 1,
  });
  catalogList.value = [];
  hasSearched.value = false;
  highlightId.value = null;
  syncUrl();
  loadArchives();
}

function search() {
  filter.page = 1;
  hasSearched.value = true;
  syncUrl();
  loadArchives();
}

function runExample(q: string) {
  filter.keyword = q;
  search();
}

function openDetail(row: Archive) {
  detailRow.value = row;
  detailVisible.value = true;
  highlightId.value = row.id;
}

function askAI(row: Archive) {
  router.push({ path: "/ai", query: { q: `请帮我解读档案：${row.TM}`, archive_id: row.id } });
}

// ── URL 状态化 ─────────────────────────────────────────────────────────────
function syncUrl() {
  const q: Record<string, string> = {};
  if (filter.keyword) q.q = filter.keyword;
  if (filter.ND) q.year = String(filter.ND);
  if (filter.MJ) q.mj = filter.MJ;
  if (filter.fonds_id) q.fonds = filter.fonds_id;
  if (filter.category_id) q.cat = filter.category_id;
  router.replace({ path: route.path, query: q });
}

function hydrateFromUrl() {
  const q = route.query;
  if (typeof q.q === "string") filter.keyword = q.q;
  if (typeof q.year === "string") filter.ND = Number(q.year) || null;
  if (typeof q.mj === "string") filter.MJ = q.mj;
  if (typeof q.fonds === "string") filter.fonds_id = q.fonds;
  if (typeof q.cat === "string") filter.category_id = q.cat;
  if (typeof q.id === "string") highlightId.value = q.id;
  if (filter.keyword || filter.ND || filter.MJ || filter.fonds_id || filter.category_id) {
    hasSearched.value = true;
  }
}

// ── 弹窗 / CRUD ─────────────────────────────────────────────────────────────
const modalVisible = ref(false);
const saving = ref(false);
const isEdit = ref(false);
const editId = ref<string | null>(null);
const formRef = ref<FormInst | null>(null);

const emptyForm = () => ({
  fonds_id: filter.fonds_id ?? "",
  catalog_id: filter.catalog_id ?? "",
  category_id: null as string | null,
  TM: "",
  QZH: "",
  RZZ: "",
  ND: null as number | null,
  WJRQ: "",
  YS: null as number | null,
  MJ: "public",
  BGQX: "permanent",
  DH: "",
});

const formData = reactive(emptyForm());

const rules = {
  fonds_id: [{ required: true, message: "请选择全宗", trigger: "change" }],
  catalog_id: [{ required: true, message: "请选择目录", trigger: "change" }],
  TM: [{ required: true, message: "请输入题名", trigger: "blur" }],
  QZH: [{ required: true, message: "请输入全宗号", trigger: "blur" }],
};

async function onFormFondsChange(id: string | null) {
  formData.catalog_id = "";
  formCatalogs.value = [];
  if (id) {
    const selectedFonds = fondsList.value.find((f) => f.id === id);
    if (selectedFonds) formData.QZH = selectedFonds.fonds_code;
    const res = await CatalogAPI.list(id);
    formCatalogs.value = res.data;
  }
}

function openModal(row: Archive | null) {
  if (row) {
    isEdit.value = true;
    editId.value = row.id;
    Object.assign(formData, {
      fonds_id: row.fonds_id,
      catalog_id: row.catalog_id,
      category_id: row.category_id,
      TM: row.TM,
      QZH: row.QZH,
      RZZ: row.RZZ ?? "",
      ND: row.ND ?? null,
      WJRQ: row.WJRQ ?? "",
      YS: row.YS ?? null,
      MJ: row.MJ,
      BGQX: row.BGQX,
      DH: row.DH ?? "",
    });
  } else {
    isEdit.value = false;
    editId.value = null;
    Object.assign(formData, emptyForm());
    if (filter.fonds_id) {
      formData.fonds_id = filter.fonds_id;
      onFormFondsChange(filter.fonds_id);
    }
    if (filter.catalog_id) formData.catalog_id = filter.catalog_id;
  }
  modalVisible.value = true;
}

async function submitForm() {
  await formRef.value?.validate();
  saving.value = true;
  try {
    if (isEdit.value && editId.value) {
      const payload: ArchiveUpdate = {
        TM: formData.TM,
        RZZ: formData.RZZ || undefined,
        ND: formData.ND ?? undefined,
        WJRQ: formData.WJRQ || undefined,
        YS: formData.YS ?? undefined,
        MJ: formData.MJ,
        BGQX: formData.BGQX,
        DH: formData.DH || undefined,
      };
      await ArchiveAPI.update(editId.value, payload);
      message.success("已更新");
    } else {
      const payload: ArchiveCreate = {
        fonds_id: formData.fonds_id,
        catalog_id: formData.catalog_id,
        category_id: formData.category_id!,
        TM: formData.TM,
        QZH: formData.QZH,
        RZZ: formData.RZZ || undefined,
        ND: formData.ND ?? undefined,
        WJRQ: formData.WJRQ || undefined,
        YS: formData.YS ?? undefined,
        MJ: formData.MJ,
        BGQX: formData.BGQX,
        DH: formData.DH || undefined,
      };
      await ArchiveAPI.create(payload);
      message.success("已创建");
    }
    modalVisible.value = false;
    await loadArchives();
  } finally {
    saving.value = false;
  }
}

function confirmDelete(row: Archive) {
  dialog.warning({
    title: "删除确认",
    content: `确定删除「${row.TM}」？（软删除）`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await ArchiveAPI.remove(row.id);
      message.success("已删除");
      detailVisible.value = false;
      await loadArchives();
    },
  });
}

async function loadArchives() {
  loading.value = true;
  try {
    const params = {
      ...(filter.fonds_id ? { fonds_id: filter.fonds_id } : {}),
      ...(filter.catalog_id ? { catalog_id: filter.catalog_id } : {}),
      ...(filter.category_id ? { category_id: filter.category_id } : {}),
      ...(filter.ND ? { ND: filter.ND } : {}),
      ...(filter.keyword ? { keyword: filter.keyword } : {}),
      ...(filter.MJ ? { MJ: filter.MJ } : {}),
      ...(filter.status ? { status: filter.status } : {}),
      page: filter.page,
      page_size: filter.page_size,
    };
    const res = await ArchiveAPI.list(params);
    archiveList.value = res.data.items;
    total.value = res.data.total;
  } finally {
    loading.value = false;
  }
}

async function loadRefData() {
  const [fondsRes, catRes] = await Promise.all([FondsAPI.list(), CategoryAPI.list()]);
  fondsList.value = fondsRes.data;
  categoryList.value = catRes.data;
}

watch(highlightId, async (id) => {
  if (!id) return;
  const found = archiveList.value.find((a) => a.id === id);
  if (found) {
    detailRow.value = found;
    detailVisible.value = true;
  } else {
    try {
      const res = await ArchiveAPI.get(id);
      detailRow.value = res.data;
      detailVisible.value = true;
    } catch { /* ignore */ }
  }
});

onMounted(async () => {
  hydrateFromUrl();
  await loadRefData();
  await loadArchives();
});
</script>
