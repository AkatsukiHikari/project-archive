<template>
  <DevPlaceholder title="出入库记录" description="档案出库与入库记录管理" icon="heroicons:arrows-right-left" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
