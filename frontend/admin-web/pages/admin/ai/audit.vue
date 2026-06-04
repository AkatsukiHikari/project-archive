<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="AI 操作审计"
      description="所有 AI 动作的端到端可追溯日志：会话查询 / Tool 回调 / Patch 全生命周期 / 评测运行"
      icon="heroicons:document-magnifying-glass"
    />

    <ProTable
      :columns="columns"
      :data="logs"
      :loading="loading"
      empty-content="暂无 AI 审计日志"
    >
      <template #toolbar-left>
        <NSelect
          v-model:value="actionFilter"
          :options="ACTION_OPTIONS"
          class="w-48"
          placeholder="动作"
          clearable
          @update:value="reload"
        />
      </template>
    </ProTable>
  </div>
</template>

<script setup lang="tsx">
import { computed, onMounted, ref } from "vue";
import { NSelect, NTag } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { AuditAPI, type AuditLog } from "@/api/audit";

definePageMeta({ layout: "admin", middleware: "auth" });

const ACTION_OPTIONS = [
  { label: "AI 会话查询", value: "ai_chat_query" },
  { label: "AI Tool 回调", value: "ai_tool_call" },
  { label: "AI Patch 提交", value: "ai_patch_create" },
  { label: "AI Patch 通过", value: "ai_patch_approve" },
  { label: "AI Patch 驳回", value: "ai_patch_reject" },
  { label: "AI 评测运行", value: "ai_eval_run" },
];

const logs = ref<AuditLog[]>([]);
const loading = ref(false);
const actionFilter = ref<string | null>("ai_chat_query");

const columns = computed(() => [
  {
    title: "动作",
    key: "action",
    width: 140,
    render: (row: AuditLog) => {
      const opt = ACTION_OPTIONS.find((o) => o.value === row.action);
      return <NTag size="small" bordered={false}>{opt?.label ?? row.action}</NTag>;
    },
  },
  { title: "模块", key: "module", width: 80 },
  { title: "状态", key: "status", width: 80 },
  { title: "IP", key: "ip_address", width: 130 },
  {
    title: "详情",
    key: "details",
    render: (row: AuditLog) => {
      const d = (row as any).details ?? {};
      const parts: string[] = [];
      if (d.scenario_code) parts.push(`场景=${d.scenario_code}`);
      if (d.model_tier) parts.push(`档位=${d.model_tier}`);
      if (d.workflow_version) parts.push(`wf=${d.workflow_version}`);
      if (d.query) parts.push(`问="${String(d.query).slice(0, 30)}"`);
      return parts.join(" · ") || "—";
    },
  },
  {
    title: "时间",
    key: "create_time",
    width: 160,
    render: (row: AuditLog) => new Date(row.create_time).toLocaleString("zh-CN"),
  },
]);

const AI_ACTIONS = new Set(ACTION_OPTIONS.map((o) => o.value));

const reload = async () => {
  loading.value = true;
  try {
    // 服务端 action 过滤；空选时降级到 module=ai 拉所有 AI 行为
    const res = actionFilter.value
      ? await AuditAPI.list({ action: actionFilter.value, limit: 200 })
      : await AuditAPI.list({ module: "ai", limit: 200 });
    const all = (res.data ?? []) as AuditLog[];
    logs.value = all.filter((l) => AI_ACTIONS.has(l.action));
  } catch {
    logs.value = [];
  } finally {
    loading.value = false;
  }
};

onMounted(() => reload());
</script>
