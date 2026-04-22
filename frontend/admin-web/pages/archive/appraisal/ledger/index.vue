<template>
  <DevPlaceholder title="鉴定台账" description="查看鉴定工作台账" icon="heroicons:book-open" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
