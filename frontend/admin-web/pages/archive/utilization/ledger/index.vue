<template>
  <DevPlaceholder title="利用台账" description="查看档案利用台账汇总" icon="heroicons:book-open" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
