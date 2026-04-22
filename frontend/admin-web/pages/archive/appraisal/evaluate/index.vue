<template>
  <DevPlaceholder title="鉴定工作" description="档案鉴定工作记录与意见" icon="heroicons:clipboard-document-list" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
