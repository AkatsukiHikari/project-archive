<template>
  <NTag :type="meta.type" size="small" round>
    <template #icon><Icon :name="meta.icon" class="w-3.5 h-3.5" /></template>
    {{ meta.label }}
  </NTag>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { NTag } from "naive-ui";
import type { TransferStatus } from "@/api/collection";

const props = defineProps<{ status: TransferStatus | string }>();

type TagType = "default" | "info" | "success" | "warning" | "error";
const MAP: Record<string, { label: string; type: TagType; icon: string }> = {
  draft: { label: "草稿", type: "default", icon: "heroicons:pencil-square" },
  submitted: { label: "待接收", type: "info", icon: "heroicons:paper-airplane" },
  received: { label: "已签收", type: "warning", icon: "heroicons:clipboard-document-check" },
  accepted: { label: "已接收入库", type: "success", icon: "heroicons:check-badge" },
  returned: { label: "已退回", type: "error", icon: "heroicons:arrow-uturn-left" },
};

const meta = computed(
  () => MAP[props.status] ?? { label: props.status, type: "default" as TagType, icon: "heroicons:tag" },
);
</script>
