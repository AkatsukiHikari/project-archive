<template>
  <DevPlaceholder title="复制申请" description="档案复制申请管理" icon="heroicons:document-duplicate" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
