<template>
  <DevPlaceholder title="元数据方案" description="档案元数据标准方案管理" icon="heroicons:variable" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
