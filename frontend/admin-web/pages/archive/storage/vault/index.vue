<template>
  <DevPlaceholder title="库房管理" description="库房信息架位及环境管理" icon="heroicons:home-modern" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
