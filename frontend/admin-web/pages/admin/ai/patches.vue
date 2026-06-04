<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="AI 操作审核队列"
      description="AI 生成的写操作（自动挂接 / 自动编目 / 知识库变更）落地前都先在这里排队，由人工审核"
      icon="heroicons:queue-list"
    />

    <ProTable
      :columns="columns"
      :data="patches"
      :loading="loading"
      empty-content="暂无待审 AI 操作（P3 上线后将有数据）"
    >
      <template #toolbar-left>
        <NSelect
          v-model:value="statusFilter"
          :options="STATUS_OPTIONS"
          class="w-32"
          placeholder="状态"
          clearable
          @update:value="reload"
        />
        <NSelect
          v-model:value="scenarioFilter"
          :options="SCENARIO_OPTIONS"
          class="w-32"
          placeholder="场景"
          clearable
          @update:value="reload"
        />
      </template>
      <template #toolbar-right>
        <NTag :bordered="false" type="info" size="small">
          <template #icon><Icon name="heroicons:information-circle" class="w-3.5 h-3.5" /></template>
          P3 实装后开放审批
        </NTag>
      </template>
    </ProTable>
  </div>
</template>

<script setup lang="tsx">
import { computed, onMounted, ref } from "vue";
import { NSelect, NTag } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { listPatches, type PatchListItem } from "@/api/ai_admin";

definePageMeta({ layout: "admin", middleware: "auth" });

const STATUS_OPTIONS = [
  { label: "待审", value: "pending" },
  { label: "通过", value: "approved" },
  { label: "驳回", value: "rejected" },
  { label: "已落库", value: "applied" },
  { label: "失败", value: "failed" },
];

const SCENARIO_OPTIONS = [
  { label: "自动挂接", value: "attach" },
  { label: "自动编目", value: "catalog" },
  { label: "知识库管理", value: "kb_manage" },
];

const patches = ref<PatchListItem[]>([]);
const loading = ref(false);
const statusFilter = ref<string | null>("pending");
const scenarioFilter = ref<string | null>(null);

const columns = computed(() => [
  { title: "场景", key: "scenario_code", width: 110 },
  { title: "目标", key: "target_type", width: 120 },
  { title: "操作", key: "operation", width: 80 },
  {
    title: "状态",
    key: "status",
    width: 90,
    render: (row: PatchListItem) => {
      const map: Record<string, { type: "default" | "info" | "success" | "warning" | "error"; label: string }> = {
        pending:  { type: "warning", label: "待审" },
        approved: { type: "success", label: "通过" },
        rejected: { type: "error", label: "驳回" },
        applied:  { type: "success", label: "已落库" },
        failed:   { type: "error", label: "失败" },
      };
      const meta = map[row.status] ?? { type: "default", label: row.status };
      return <NTag size="small" type={meta.type} bordered={false}>{meta.label}</NTag>;
    },
  },
  {
    title: "AI 置信度",
    key: "confidence",
    width: 100,
    render: (row: PatchListItem) => row.confidence != null ? `${(row.confidence * 100).toFixed(1)}%` : "—",
  },
  { title: "闸门", key: "gate", width: 80 },
  { title: "Workflow", key: "workflow_version", width: 120 },
  {
    title: "提出时间",
    key: "create_time",
    width: 160,
    render: (row: PatchListItem) => new Date(row.create_time).toLocaleString("zh-CN"),
  },
]);

const reload = async () => {
  loading.value = true;
  try {
    const res = await listPatches({
      status: statusFilter.value ?? undefined,
      scenario_code: scenarioFilter.value ?? undefined,
      page: 1,
      size: 50,
    });
    patches.value = res.data.items;
  } finally {
    loading.value = false;
  }
};

onMounted(() => reload());
</script>
