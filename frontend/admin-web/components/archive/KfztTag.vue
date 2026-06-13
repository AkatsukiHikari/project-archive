<template>
  <NTag v-if="value" :type="meta.type" size="small" round>{{ value }}</NTag>
  <span v-else class="text-xs text-gray-400">未鉴定</span>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { NTag } from "naive-ui";

const props = defineProps<{ value?: string | null }>();

type TagType = "default" | "info" | "success" | "warning" | "error";
const MAP: Record<string, TagType> = {
  开放: "success",
  控制使用: "warning",
  延期开放: "info",
  不开放: "error",
};

const meta = computed(() => ({ type: MAP[props.value ?? ""] ?? ("default" as TagType) }));
</script>
