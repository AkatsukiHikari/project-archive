<template>
  <DevPlaceholder title="档案统计" description="档案各维度统计分析" icon="heroicons:chart-bar" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
