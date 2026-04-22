<template>
  <DevPlaceholder title="编研项目" description="档案编研项目立项与管理" icon="heroicons:folder-open" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
