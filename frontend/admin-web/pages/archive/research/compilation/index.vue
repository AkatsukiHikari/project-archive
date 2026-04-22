<template>
  <DevPlaceholder title="专题汇编" description="专题档案汇编成果管理" icon="heroicons:book-open" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
