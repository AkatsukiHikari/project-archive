<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="编研成果库"
      description="通用编研成果库：大事记、组织沿革、专题汇编等成果的在线文档编纂、AI 起草、审核与发布"
      icon="heroicons:book-open"
    />

    <!-- 工具栏 -->
    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <NSelect v-model:value="filterType" :options="typeOptions" placeholder="全部体裁" clearable style="width: 150px" @update:value="loadResults" />
      <NSelect v-model:value="filterStatus" :options="statusFilterOptions" placeholder="全部状态" clearable style="width: 140px" @update:value="loadResults" />
      <NInput v-model:value="filterKeyword" placeholder="成果标题关键词" clearable style="width: 220px" @keyup.enter="loadResults" />
      <NButton tertiary @click="loadResults">
        <template #icon><Icon name="heroicons:magnifying-glass" class="w-4 h-4" /></template>
        查询
      </NButton>
      <div class="flex-1" />
      <NButton tertiary @click="goTemplates">
        <template #icon><Icon name="heroicons:document-duplicate" class="w-4 h-4" /></template>
        编研模板
      </NButton>
      <NButton type="primary" @click="openCreate">
        <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
        新建成果
      </NButton>
    </div>

    <!-- 成果列表 -->
    <div class="pro-card p-5">
      <ProTable :columns="columns" :data="results" :loading="loading" :page-size="10" size="small" :scroll-x="1100" />
    </div>

    <!-- 新建成果向导 -->
    <NModal v-model:show="showCreate" preset="card" title="新建编研成果" style="width: 640px; max-width: 95vw" :mask-closable="false">
      <div class="flex flex-col gap-4">
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">成果标题 <span class="text-red-500">*</span></span>
          <NInput v-model:value="form.title" placeholder="如：XX市建市四十周年大事记" />
        </div>
        <div class="grid grid-cols-2 gap-4">
          <div class="flex flex-col gap-1">
            <span class="text-sm font-medium">体裁 <span class="text-red-500">*</span></span>
            <NSelect v-model:value="form.result_type" :options="typeOptions" @update:value="onTypeChange" />
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-sm font-medium">所属项目</span>
            <NSelect v-model:value="form.project_id" :options="projectOptions" filterable clearable placeholder="可不关联" />
          </div>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">起始模板</span>
          <NSelect v-model:value="form.template_id" :options="templateOptions" clearable placeholder="空白文档（不选模板）" />
          <span class="text-xs text-gray-400">选择模板可套用现成的文档结构与版式，快速开始编纂。</span>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <NButton @click="showCreate = false">取消</NButton>
          <NButton type="primary" :loading="creating" @click="submitCreate">创建并编辑</NButton>
        </div>
      </template>
    </NModal>

    <!-- 在线文档编辑器 -->
    <ResearchResultEditor v-model:show="showEditor" :result-id="editingId" @saved="loadResults" />
  </div>
</template>

<script setup lang="tsx">
import { h, onMounted, reactive, ref } from "vue";
import { NButton, NInput, NModal, NPopconfirm, NSelect, useMessage } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { ResearchResultEditor, ResearchTypeTag, ResultStatusTag } from "@/components/archive";
import {
  RESULT_TYPES, ResearchProjectAPI, ResearchResultAPI, ResearchTemplateAPI,
  type ResearchProject, type ResearchResultItem, type ResearchTemplate,
  type ResultAction, type ResultStatus, type ResultType,
} from "@/api/research";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const router = useRouter();
const route = useRoute();

const typeOptions = RESULT_TYPES.map((t) => ({ label: t, value: t }));
const statusFilterOptions = [
  { label: "草稿", value: "draft" },
  { label: "审核中", value: "reviewing" },
  { label: "已定稿", value: "finalized" },
  { label: "已发布", value: "published" },
];

// ── 列表 ──────────────────────────────────────────────────────────────────────
const loading = ref(false);
const results = ref<ResearchResultItem[]>([]);
const filterType = ref<ResultType | null>(null);
const filterStatus = ref<ResultStatus | null>(null);
const filterKeyword = ref("");

async function loadResults() {
  loading.value = true;
  try {
    const res = await ResearchResultAPI.list({
      result_type: filterType.value ?? undefined,
      status: filterStatus.value ?? undefined,
      keyword: filterKeyword.value || undefined,
      project_id: (route.query.project_id as string) || undefined,
      limit: 200,
    });
    results.value = res.data.items;
  } finally {
    loading.value = false;
  }
}

const columns: DataTableColumns<ResearchResultItem> = [
  { title: "成果标题", key: "title", ellipsis: { tooltip: true }, minWidth: 240 },
  { title: "体裁", key: "result_type", width: 120, render: (r) => h(ResearchTypeTag, { type: r.result_type }) },
  { title: "所属项目", key: "project_title", width: 180, ellipsis: { tooltip: true }, render: (r) => r.project_title || "—" },
  { title: "引用档案", key: "archive_count", width: 90, render: (r) => `${r.archive_count} 件` },
  { title: "状态", key: "status", width: 100, render: (r) => h(ResultStatusTag, { status: r.status }) },
  { title: "创建时间", key: "create_time", width: 110, render: (r) => r.create_time?.slice(0, 10) },
  {
    title: "操作", key: "actions", width: 280, fixed: "right",
    render: (r) => h("div", { class: "flex flex-wrap gap-1" }, [
      h(NButton, { size: "small", type: "primary", tertiary: true, onClick: () => openEditor(r.id) },
        { default: () => (canEdit(r) ? "编纂" : "查看") }),
      ...workflowButtons(r),
      h(NPopconfirm, { onPositiveClick: () => removeResult(r.id) }, {
        trigger: () => h(NButton, { size: "small", tertiary: true, type: "error" }, { default: () => "删除" }),
        default: () => "确认删除该成果？",
      }),
    ]),
  },
];

function canEdit(r: ResearchResultItem): boolean {
  return r.status === "draft" || r.status === "reviewing";
}

function workflowButtons(r: ResearchResultItem) {
  const btn = (label: string, action: ResultAction, type: "primary" | "warning") =>
    h(NButton, { size: "small", tertiary: true, type, onClick: () => transition(r.id, action, label) }, { default: () => label });
  if (r.status === "draft") return [btn("提交审核", "submit", "primary")];
  if (r.status === "reviewing") return [btn("定稿", "finalize", "primary")];
  if (r.status === "finalized") return [btn("发布", "publish", "primary"), btn("撤回", "reopen", "warning")];
  if (r.status === "published") return [btn("撤回", "reopen", "warning")];
  return [];
}

async function transition(id: string, action: ResultAction, label: string) {
  const res = await ResearchResultAPI.transition(id, action);
  if (res.code === 0) {
    message.success(`${label}成功`);
    loadResults();
  } else {
    message.error(res.message);
  }
}

async function removeResult(id: string) {
  const res = await ResearchResultAPI.remove(id);
  if (res.code === 0) {
    message.success("已删除");
    loadResults();
  } else {
    message.error(res.message);
  }
}

// ── 编辑器 ────────────────────────────────────────────────────────────────────
const showEditor = ref(false);
const editingId = ref<string | null>(null);

function openEditor(id: string) {
  editingId.value = id;
  showEditor.value = true;
}

// ── 新建向导 ──────────────────────────────────────────────────────────────────
const showCreate = ref(false);
const creating = ref(false);
const form = reactive<{
  title: string;
  result_type: ResultType;
  project_id: string | null;
  template_id: string | null;
}>({ title: "", result_type: "专题汇编", project_id: null, template_id: null });

function openCreate() {
  form.title = "";
  form.result_type = "专题汇编";
  form.project_id = (route.query.project_id as string) || null;
  form.template_id = null;
  refreshTemplateOptions();
  showCreate.value = true;
}

function onTypeChange() {
  form.template_id = null;
  refreshTemplateOptions();
}

async function submitCreate() {
  if (!form.title.trim()) return message.warning("请填写成果标题");
  creating.value = true;
  try {
    const res = await ResearchResultAPI.create({
      title: form.title.trim(),
      result_type: form.result_type,
      project_id: form.project_id || null,
      template_id: form.template_id || null,
    });
    if (res.code === 0) {
      showCreate.value = false;
      loadResults();
      openEditor(res.data.id);
    } else {
      message.error(res.message);
    }
  } finally {
    creating.value = false;
  }
}

// ── 项目 / 模板下拉 ────────────────────────────────────────────────────────────
const projectOptions = ref<{ label: string; value: string }[]>([]);
const allTemplates = ref<ResearchTemplate[]>([]);
const templateOptions = ref<{ label: string; value: string }[]>([]);

function refreshTemplateOptions() {
  templateOptions.value = allTemplates.value
    .filter((t) => t.result_type === form.result_type)
    .map((t) => ({ label: t.is_builtin ? `${t.name}（内置）` : t.name, value: t.id }));
}

async function loadOptions() {
  const [p, t] = await Promise.all([ResearchProjectAPI.list(), ResearchTemplateAPI.list()]);
  projectOptions.value = (p.data ?? []).map((x: ResearchProject) => ({ label: x.title, value: x.id }));
  allTemplates.value = t.data ?? [];
}

function goTemplates() {
  router.push("/archive/research/template");
}

onMounted(() => {
  loadResults();
  loadOptions();
});
</script>
