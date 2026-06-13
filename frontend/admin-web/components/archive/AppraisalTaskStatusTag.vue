<template>
  <NTag :type="meta.type" size="small" round>
    <template #icon><Icon :name="meta.icon" class="w-3.5 h-3.5" /></template>
    {{ meta.label }}
  </NTag>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { NTag } from "naive-ui";
import type { TaskStatus } from "@/api/appraisal";

const props = defineProps<{ status: TaskStatus | string }>();

type TagType = "default" | "info" | "success" | "warning" | "error";
const MAP: Record<string, { label: string; type: TagType; icon: string }> = {
  pending: { label: "待鉴定", type: "default", icon: "heroicons:clock" },
  ai_running: { label: "AI 预鉴定中", type: "info", icon: "heroicons:sparkles" },
  ai_done: { label: "AI 预鉴完成", type: "info", icon: "heroicons:sparkles" },
  submitted: { label: "待审核", type: "warning", icon: "heroicons:paper-airplane" },
  approved: { label: "已通过", type: "success", icon: "heroicons:check-badge" },
  rejected: { label: "已驳回", type: "error", icon: "heroicons:arrow-uturn-left" },
};

const meta = computed(
  () => MAP[props.status] ?? { label: props.status, type: "default" as TagType, icon: "heroicons:tag" },
);
</script>
