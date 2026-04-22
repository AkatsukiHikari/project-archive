<template>
  <DevPlaceholder title="目录管理" description="管理档案目录，对档案分组编目" icon="heroicons:bars-3-bottom-left" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
