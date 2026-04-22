<template>
  <DevPlaceholder title="销毁执行" description="档案销毁执行记录" icon="heroicons:fire" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
