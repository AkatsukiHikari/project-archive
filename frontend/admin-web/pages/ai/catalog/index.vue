<template>
  <div class="flex flex-col gap-2.5">
    <div class="flex items-center justify-between">
      <div class="flex items-center gap-2">
        <div
          class="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
          style="background: linear-gradient(135deg, oklch(var(--p)) 0%, oklch(var(--p)/0.72) 100%)"
        >
          <Icon name="heroicons:document-plus" class="w-4 h-4 text-white" />
        </div>
        <h1 class="text-[15px] font-semibold" style="color: var(--semi-color-text-0)">智能著录</h1>
      </div>
      <div class="flex items-center gap-2">
        <NSelect v-model:value="docSource" :options="sourceOptions" size="small" style="width: 130px" @update:value="load" />
        <NSwitch v-model:value="onlyIssues" size="small" @update:value="load">
          <template #checked>仅看待处理</template>
          <template #unchecked>全部档案</template>
        </NSwitch>
        <NButton type="primary" size="small" @click="ingestShow = true">
          <template #icon><Icon name="heroicons:sparkles" class="w-4 h-4" /></template>
          自动录入
        </NButton>
        <NButton text size="small" :loading="loading" @click="load">
          <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
          刷新
        </NButton>
      </div>
    </div>

    <div class="pro-card p-2">
      <NDataTable :columns="columns" :data="rows" :loading="loading" :pagination="pagination" :row-key="(r: CatalogCandidate) => r.id" size="small" />
    </div>

    <AiCatalogDrawer v-model:show="drawerShow" :archive="target" @applied="load" />
    <AutoIngestModal v-model:show="ingestShow" @created="load" />
  </div>
</template>

<script setup lang="tsx">
import { h, onMounted, reactive, ref } from "vue";
import { NButton, NDataTable, NSelect, NSwitch, NTag } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AiCatalogDrawer, AutoIngestModal } from "@/components/archive";
import { CatalogAPI, type CatalogCandidate } from "@/api/catalog";

const router = useRouter();

definePageMeta({
  layout: "archive",
  middleware: "auth",
  breadcrumb: [
    { name: "AI 档案助手", path: "/ai" },
    { name: "智能著录", path: "/ai/catalog" },
  ],
});
useHead({ title: "智能著录" });

const rows = ref<CatalogCandidate[]>([]);
const loading = ref(false);
const docSource = ref("all");
const onlyIssues = ref(false);
const drawerShow = ref(false);
const ingestShow = ref(false);
const target = ref<{ id: string; doc_source: "staging" | "formal"; DH?: string; TM: string; category_id?: string | null } | null>(null);

const sourceOptions = [
  { label: "全部库", value: "all" },
  { label: "暂存库", value: "staging" },
  { label: "正式库", value: "formal" },
];

const STATUS_META: Record<string, { label: string; type: "default" | "info" | "warning" | "error" | "success" }> = {
  no_source: { label: "无原文", type: "default" },
  need_ocr: { label: "待OCR", type: "info" },
  empty: { label: "待著录", type: "error" },
  missing: { label: "缺字段", type: "warning" },
  complete: { label: "已完整", type: "success" },
};

const pagination = reactive({
  pageSize: 20,
  showSizePicker: true,
  pageSizes: [20, 50, 100],
  prefix: ({ itemCount }: { itemCount: number }) => `共 ${itemCount} 条`,
});

const columns: DataTableColumns<CatalogCandidate> = [
  {
    title: "来源", key: "doc_source", width: 70,
    render: (r) => h(NTag, { size: "small", round: true, type: r.doc_source === "formal" ? "success" : "default", bordered: false },
      { default: () => (r.doc_source === "formal" ? "正式库" : "暂存库") }),
  },
  { title: "档号", key: "DH", width: 190, render: (r) => h("span", { class: "font-mono text-xs" }, r.DH || "—") },
  { title: "题名", key: "TM", ellipsis: { tooltip: true }, render: (r) => r.TM || "—" },
  { title: "全宗", key: "QZH", width: 80, render: (r) => r.QZH || "—" },
  { title: "年度", key: "ND", width: 70, render: (r) => (r.ND ? String(r.ND) : "—") },
  {
    title: "完整度", key: "completeness", width: 130,
    render: (r) => {
      const m = STATUS_META[r.status] ?? STATUS_META.missing;
      return h("div", { class: "flex items-center gap-2" }, [
        h(NTag, { size: "small", round: true, type: m.type, bordered: false }, { default: () => m.label }),
        h("span", { class: "text-[11px] tabular-nums", style: "color:var(--semi-color-text-3)" }, r.total ? `${r.filled}/${r.total}` : ""),
      ]);
    },
  },
  {
    title: "操作", key: "actions", width: 170,
    render: (r) => h("div", { class: "flex gap-1.5" }, [
      h(NButton, {
        size: "tiny", tertiary: true, type: "primary",
        disabled: !r.attachment_count,
        title: r.attachment_count ? "查看原文" : "该档案暂无数字化原文",
        onClick: () => router.push(`/archive/reader?id=${r.id}`),
      }, { default: () => "查看原文" }),
      h(NButton, {
        size: "tiny", type: "primary", tertiary: true,
        disabled: !r.attachment_count,
        title: r.attachment_count ? "AI 著录" : "无原文，无法 AI 著录",
        onClick: () => openDrawer(r),
      }, { default: () => "AI 著录" }),
    ]),
  },
];

function openDrawer(r: CatalogCandidate) {
  target.value = { id: r.id, doc_source: r.doc_source, DH: r.DH, TM: r.TM, category_id: r.category_id ?? null };
  drawerShow.value = true;
}

async function load() {
  loading.value = true;
  try {
    const res = await CatalogAPI.candidates({ doc_source: docSource.value, only_issues: onlyIssues.value, limit: 200 });
    rows.value = res.data.items;
  } finally {
    loading.value = false;
  }
}

onMounted(load);
</script>
