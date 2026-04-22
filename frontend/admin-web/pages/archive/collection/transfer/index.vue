<template>
  <DevPlaceholder title="归档移交" description="接收各部门移交档案，记录移交清单" icon="heroicons:arrow-down-tray" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
