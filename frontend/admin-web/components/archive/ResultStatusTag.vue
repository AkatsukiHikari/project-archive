<template>
  <NTag :type="meta.type" size="small" round>
    <template #icon><Icon :name="meta.icon" class="w-3.5 h-3.5" /></template>
    {{ meta.label }}
  </NTag>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { NTag } from "naive-ui";
import type { ResultStatus } from "@/api/research";

const props = defineProps<{ status: ResultStatus | string }>();

type TagType = "default" | "info" | "success" | "warning" | "error";
const MAP: Record<string, { label: string; type: TagType; icon: string }> = {
  draft: { label: "草稿", type: "default", icon: "heroicons:pencil-square" },
  reviewing: { label: "审核中", type: "warning", icon: "heroicons:paper-airplane" },
  finalized: { label: "已定稿", type: "info", icon: "heroicons:check-badge" },
  published: { label: "已发布", type: "success", icon: "heroicons:globe-alt" },
};

const meta = computed(
  () => MAP[props.status] ?? { label: props.status, type: "default" as TagType, icon: "heroicons:tag" },
);
</script>
