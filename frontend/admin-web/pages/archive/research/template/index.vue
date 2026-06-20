<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="编研模板"
      description="成果文档的可复用骨架：系统内置常用体裁模板，也可把写好的成果版式存为自有模板，快速开始编纂"
      icon="heroicons:document-duplicate"
    />

    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <NSelect v-model:value="filterType" :options="typeOptions" placeholder="全部体裁" clearable style="width: 150px" @update:value="load" />
      <NButton tertiary @click="load">
        <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
        刷新
      </NButton>
      <div class="flex-1" />
      <NButton type="primary" @click="openCreate">
        <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
        新建模板
      </NButton>
    </div>

    <div class="pro-card p-5">
      <ProTable :columns="columns" :data="templates" :loading="loading" :page-size="10" size="small" />
    </div>

    <ResearchTemplateEditor v-model:show="showEditor" :template-id="editingId" @saved="load" />
  </div>
</template>

<script setup lang="tsx">
import { h, onMounted, ref } from "vue";
import { NButton, NPopconfirm, NSelect, NTag, useMessage } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { ResearchTemplateEditor, ResearchTypeTag } from "@/components/archive";
import {
  RESULT_TYPES, ResearchTemplateAPI,
  type ResearchTemplate, type ResultType,
} from "@/api/research";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const typeOptions = RESULT_TYPES.map((t) => ({ label: t, value: t }));

const loading = ref(false);
const templates = ref<ResearchTemplate[]>([]);
const filterType = ref<ResultType | null>(null);

async function load() {
  loading.value = true;
  try {
    const res = await ResearchTemplateAPI.list({ result_type: filterType.value ?? undefined });
    templates.value = res.data;
  } finally {
    loading.value = false;
  }
}

const columns: DataTableColumns<ResearchTemplate> = [
  { title: "模板名称", key: "name", width: 200, ellipsis: { tooltip: true } },
  { title: "体裁", key: "result_type", width: 120, render: (r) => h(ResearchTypeTag, { type: r.result_type }) },
  {
    title: "来源", key: "is_builtin", width: 100,
    render: (r) => h(NTag, { type: r.is_builtin ? "info" : "default", size: "small", round: true },
      { default: () => (r.is_builtin ? "内置" : "自有") }),
  },
  { title: "说明", key: "description", ellipsis: { tooltip: true }, render: (r) => r.description || "—" },
  { title: "创建时间", key: "create_time", width: 110, render: (r) => r.create_time?.slice(0, 10) },
  {
    title: "操作", key: "actions", width: 170,
    render: (r) => h("div", { class: "flex gap-1" }, [
      h(NButton, { size: "small", type: "primary", tertiary: true, onClick: () => openEdit(r.id) },
        { default: () => (r.is_builtin ? "查看" : "编辑") }),
      r.is_builtin
        ? null
        : h(NPopconfirm, { onPositiveClick: () => remove(r.id) }, {
            trigger: () => h(NButton, { size: "small", tertiary: true, type: "error" }, { default: () => "删除" }),
            default: () => "确认删除该模板？",
          }),
    ]),
  },
];

const showEditor = ref(false);
const editingId = ref<string | null>(null);

function openCreate() {
  editingId.value = null;
  showEditor.value = true;
}

function openEdit(id: string) {
  editingId.value = id;
  showEditor.value = true;
}

async function remove(id: string) {
  const res = await ResearchTemplateAPI.remove(id);
  if (res.code === 0) {
    message.success("已删除");
    load();
  } else {
    message.error(res.message);
  }
}

onMounted(load);
</script>
