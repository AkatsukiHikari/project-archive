<template>
  <DevPlaceholder title="鉴定计划" description="档案价值鉴定工作计划管理" icon="heroicons:calendar" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
