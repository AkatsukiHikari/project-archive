<template>
  <DevPlaceholder title="年报管理" description="档案工作年度报告编制" icon="heroicons:document-chart-bar" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
