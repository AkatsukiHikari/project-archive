<template>
  <DevPlaceholder title="整理台账" description="查看整理工作台账记录" icon="heroicons:book-open" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
