<template>
  <DevPlaceholder title="四性检测" description="电子档案真实性完整性可用性安全性检测" icon="heroicons:shield-check" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
