<template>
  <DevPlaceholder title="收集台账" description="查看全部档案收集登记台账" icon="heroicons:book-open" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
