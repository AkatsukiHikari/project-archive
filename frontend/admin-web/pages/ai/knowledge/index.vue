<template>
  <div class="flex flex-col gap-2.5">
    <!-- 状态条 -->
    <div class="flex items-center gap-3">
      <div
        class="w-7 h-7 rounded-lg flex items-center justify-center shrink-0"
        style="background: linear-gradient(135deg, oklch(var(--p)) 0%, oklch(var(--p)/0.72) 100%)"
      >
        <Icon name="heroicons:book-open" class="w-4 h-4 text-white" />
      </div>
      <h1 class="text-[15px] font-semibold" style="color: var(--semi-color-text-0)">AI 知识库</h1>
      <NTag v-if="status?.name" size="small" round :bordered="false">{{ status.name }}</NTag>
      <span v-if="status" class="text-[12px]" style="color: var(--semi-color-text-3)">{{ status.doc_count ?? "—" }} 篇文档</span>
      <NTag v-if="unsyncedTotal > 0" size="small" type="warning" round :bordered="false">{{ unsyncedTotal }} 条档案未同步</NTag>
      <div class="flex-1" />
      <NButton type="primary" size="small" :loading="syncing" @click="doSync">
        <template #icon><Icon name="heroicons:cloud-arrow-up" class="w-4 h-4" /></template>
        一键全量同步
      </NButton>
      <NButton text size="small" :loading="loadingStatus" @click="refreshAll">
        <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
        刷新
      </NButton>
    </div>

    <NTabs v-model:value="tab" type="line" size="small">
      <!-- ── 文档清单 ─────────────────────────────────────── -->
      <NTabPane name="docs" tab="文档清单">
        <div class="flex flex-col gap-2.5">
          <div class="flex items-center gap-2">
            <NInput v-model:value="docKeyword" size="small" placeholder="搜索文档名…" clearable style="width: 260px" @keydown.enter="loadDocs" @clear="loadDocs">
              <template #prefix><Icon name="heroicons:magnifying-glass" class="w-3.5 h-3.5" style="color: var(--semi-color-text-3)" /></template>
            </NInput>
            <NButton size="small" @click="loadDocs">搜索</NButton>
            <div class="flex-1" />
            <NUpload :show-file-list="false" :custom-request="doUpload" accept=".pdf,.docx,.doc,.txt,.md">
              <NButton size="small" type="primary" secondary :loading="uploading">
                <template #icon><Icon name="heroicons:document-plus" class="w-4 h-4" /></template>
                上传制度文件
              </NButton>
            </NUpload>
          </div>
          <div class="pro-card p-2">
            <NDataTable :columns="docColumns" :data="docs" :loading="docsLoading" :pagination="docPagination" :row-key="(r: KBDoc) => r.id" size="small" remote @update:page="onDocPage" />
          </div>
        </div>
      </NTabPane>

      <!-- ── 命中测试 ─────────────────────────────────────── -->
      <NTabPane name="hit" tab="命中测试">
        <div class="flex flex-col gap-2.5">
          <div class="flex items-center gap-2">
            <NInput v-model:value="hitQuery" size="small" placeholder="输入一个问题，看知识库召回哪些内容，例如：2023年防汛部署" style="width: 460px" @keydown.enter="runHitTest" />
            <NButton size="small" type="primary" :loading="hitLoading" @click="runHitTest">测试</NButton>
            <span v-if="hits.length" class="text-[12px]" style="color: var(--semi-color-text-3)">召回 {{ hits.length }} 个片段</span>
          </div>
          <div v-if="hitError" class="text-[12.5px]" style="color:#dc2626">{{ hitError }}</div>
          <div v-else-if="!hits.length && hitTested" class="text-[12.5px] py-6 text-center" style="color: var(--semi-color-text-3)">未召回任何片段——该问题在知识库里没有相近内容</div>
          <div v-for="(hit, i) in hits" :key="i" class="pro-card p-3 flex flex-col gap-1.5">
            <div class="flex items-center gap-2">
              <NTag size="small" :type="(hit.score ?? 0) >= 0.6 ? 'success' : (hit.score ?? 0) >= 0.4 ? 'warning' : 'default'" round :bordered="false">
                相关度 {{ ((hit.score ?? 0) * 100).toFixed(0) }}%
              </NTag>
              <span class="text-[12px] font-medium truncate" style="color: var(--semi-color-text-1)">{{ hit.document_name || "未知文档" }}</span>
            </div>
            <p class="text-[12.5px] leading-relaxed whitespace-pre-wrap break-words m-0" style="color: var(--semi-color-text-2)">{{ hit.content }}</p>
          </div>
        </div>
      </NTabPane>

      <!-- ── 未同步档案 ───────────────────────────────────── -->
      <NTabPane name="unsynced" tab="未同步档案">
        <div class="pro-card p-2">
          <NDataTable :columns="unsyncedColumns" :data="unsynced" :loading="unsyncedLoading" :pagination="{ pageSize: 20 }" :row-key="(r: KBUnsynced) => r.id" size="small" />
        </div>
      </NTabPane>
    </NTabs>
  </div>
</template>

<script setup lang="tsx">
import { h, onMounted, reactive, ref } from "vue";
import { NButton, NDataTable, NInput, NTabPane, NTabs, NTag, NUpload, useDialog, useMessage } from "naive-ui";
import type { DataTableColumns, UploadCustomRequestOptions } from "naive-ui";
import { AiAdminAPI, type KBDoc, type KBHit, type KBStatus, type KBUnsynced } from "@/api/ai";

definePageMeta({
  layout: "archive",
  middleware: "auth",
  breadcrumb: [
    { name: "AI 档案助手", path: "/ai" },
    { name: "AI 知识库", path: "/ai/knowledge" },
  ],
});
useHead({ title: "AI 知识库" });

const message = useMessage();
const dialog = useDialog();

const tab = ref("docs");
const status = ref<KBStatus | null>(null);
const loadingStatus = ref(false);
const syncing = ref(false);

// ── 文档清单 ──────────────────────────────────────────────────────────────────
const docs = ref<KBDoc[]>([]);
const docsLoading = ref(false);
const docKeyword = ref("");
const uploading = ref(false);
const docPagination = reactive({ page: 1, pageSize: 20, itemCount: 0, prefix: ({ itemCount }: { itemCount?: number }) => `共 ${itemCount ?? 0} 篇` });

const INDEXING_LABEL: Record<string, { label: string; type: "success" | "info" | "error" | "default" }> = {
  completed: { label: "已索引", type: "success" },
  error: { label: "失败", type: "error" },
  paused: { label: "已暂停", type: "default" },
};

const docColumns: DataTableColumns<KBDoc> = [
  { title: "文档", key: "name", ellipsis: { tooltip: true } },
  { title: "字数", key: "word_count", width: 90, render: (r) => (r.word_count ? r.word_count.toLocaleString() : "—") },
  {
    title: "状态", key: "indexing_status", width: 90,
    render: (r) => {
      const m = INDEXING_LABEL[r.indexing_status ?? ""] ?? { label: "处理中", type: "info" as const };
      return h(NTag, { size: "small", round: true, bordered: false, type: m.type }, { default: () => m.label });
    },
  },
  {
    title: "入库时间", key: "created_at", width: 150,
    render: (r) => (r.created_at ? new Date(r.created_at * 1000).toLocaleString("zh-CN", { month: "2-digit", day: "2-digit", hour: "2-digit", minute: "2-digit" }) : "—"),
  },
  {
    title: "操作", key: "actions", width: 80,
    render: (r) => h(NButton, {
      size: "tiny", tertiary: true, type: "error",
      onClick: () => confirmDeleteDoc(r),
    }, { default: () => "删除" }),
  },
];

async function loadDocs() {
  docsLoading.value = true;
  try {
    const res = await AiAdminAPI.kbDocuments({ page: docPagination.page, limit: docPagination.pageSize, keyword: docKeyword.value.trim() || undefined });
    docs.value = res.data.items;
    docPagination.itemCount = res.data.total;
  } finally {
    docsLoading.value = false;
  }
}

function onDocPage(p: number) {
  docPagination.page = p;
  loadDocs();
}

function confirmDeleteDoc(r: KBDoc) {
  dialog.warning({
    title: "删除确认",
    content: `确认从知识库删除「${r.name}」？来自档案同步的文档删除后可重新同步。`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await AiAdminAPI.kbDeleteDoc(r.id);
      message.success("已删除");
      refreshAll();
    },
  });
}

function doUpload({ file, onFinish, onError }: UploadCustomRequestOptions) {
  const raw = file.file;
  if (!raw) { onError(); return; }
  uploading.value = true;
  AiAdminAPI.kbUpload(raw as File)
    .then((res) => {
      if (res.code === 0) {
        message.success(`已上传「${res.data.name}」，索引完成后即可被问答引用`);
        onFinish();
        loadDocs();
      } else {
        message.error(res.message || "上传失败");
        onError();
      }
    })
    .catch(() => { message.error("上传失败"); onError(); })
    .finally(() => { uploading.value = false; });
}

// ── 命中测试 ──────────────────────────────────────────────────────────────────
const hitQuery = ref("");
const hits = ref<KBHit[]>([]);
const hitLoading = ref(false);
const hitTested = ref(false);
const hitError = ref("");

async function runHitTest() {
  const q = hitQuery.value.trim();
  if (!q) return;
  hitLoading.value = true;
  hitError.value = "";
  try {
    const res = await AiAdminAPI.kbHitTest(q);
    hits.value = res.data.records;
    hitTested.value = true;
  } catch {
    hitError.value = "命中测试失败，请确认知识库/Embedding 已配置";
  } finally {
    hitLoading.value = false;
  }
}

// ── 未同步档案 ────────────────────────────────────────────────────────────────
const unsynced = ref<KBUnsynced[]>([]);
const unsyncedTotal = ref(0);
const unsyncedLoading = ref(false);
const syncingIds = ref<Set<string>>(new Set());

const unsyncedColumns: DataTableColumns<KBUnsynced> = [
  { title: "档号", key: "DH", width: 200, render: (r) => h("span", { class: "font-mono text-xs" }, r.DH || "—") },
  { title: "题名", key: "TM", ellipsis: { tooltip: true } },
  { title: "全宗", key: "QZH", width: 90, render: (r) => r.QZH || "—" },
  { title: "年度", key: "ND", width: 70, render: (r) => (r.ND ? String(r.ND) : "—") },
  {
    title: "操作", key: "actions", width: 90,
    render: (r) => h(NButton, {
      size: "tiny", tertiary: true, type: "primary",
      loading: syncingIds.value.has(r.id),
      onClick: () => syncOne(r),
    }, { default: () => "同步" }),
  },
];

async function loadUnsynced() {
  unsyncedLoading.value = true;
  try {
    const res = await AiAdminAPI.kbUnsynced();
    unsynced.value = res.data.items;
    unsyncedTotal.value = res.data.total;
  } finally {
    unsyncedLoading.value = false;
  }
}

async function syncOne(r: KBUnsynced) {
  syncingIds.value = new Set(syncingIds.value).add(r.id);
  try {
    const res = await AiAdminAPI.kbSyncOne(r.id);
    if (res.data.ok) {
      message.success(`已同步 ${r.DH || r.TM}`);
      loadUnsynced();
      loadStatus();
    } else {
      message.error(res.data.reason || "同步失败");
    }
  } finally {
    const s = new Set(syncingIds.value);
    s.delete(r.id);
    syncingIds.value = s;
  }
}

// ── 状态 / 全量同步 ───────────────────────────────────────────────────────────
async function loadStatus() {
  loadingStatus.value = true;
  try {
    const res = await AiAdminAPI.kbStatus();
    status.value = res.data;
  } finally {
    loadingStatus.value = false;
  }
}

async function doSync() {
  syncing.value = true;
  try {
    const res = await AiAdminAPI.kbRebuild();
    if (res.code === 0) {
      message.success(`已同步 ${res.data.synced} 条档案到知识库`);
      refreshAll();
    } else {
      message.error(res.message);
    }
  } catch {
    message.error("同步失败");
  } finally {
    syncing.value = false;
  }
}

function refreshAll() {
  loadStatus();
  loadDocs();
  loadUnsynced();
}

onMounted(refreshAll);
</script>
