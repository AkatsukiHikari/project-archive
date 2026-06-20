<template>
  <NTag :type="meta.type" size="small" round :bordered="false">
    <template #icon><Icon :name="meta.icon" class="w-3.5 h-3.5" /></template>
    {{ type }}
  </NTag>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { NTag } from "naive-ui";
import type { ResultType } from "@/api/research";

const props = defineProps<{ type: ResultType | string }>();

type TagType = "default" | "info" | "success" | "warning" | "error";
const MAP: Record<string, { type: TagType; icon: string }> = {
  大事记: { type: "warning", icon: "heroicons:clock" },
  组织沿革: { type: "info", icon: "heroicons:building-office-2" },
  专题汇编: { type: "success", icon: "heroicons:book-open" },
  基础数字汇编: { type: "info", icon: "heroicons:calculator" },
  参考资料: { type: "default", icon: "heroicons:document-text" },
  全宗指南: { type: "default", icon: "heroicons:map" },
};

const meta = computed(
  () => MAP[props.type] ?? { type: "default" as TagType, icon: "heroicons:tag" },
);
</script>
