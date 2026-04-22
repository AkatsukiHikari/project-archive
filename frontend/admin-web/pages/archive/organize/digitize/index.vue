<template>
  <DevPlaceholder title="数字化加工" description="档案数字化扫描与加工管理" icon="heroicons:computer-desktop" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
