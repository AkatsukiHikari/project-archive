<template>
  <DevPlaceholder title="证明开具" description="档案内容证明文件开具" icon="heroicons:identification" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
