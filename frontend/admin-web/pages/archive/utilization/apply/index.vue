<template>
  <DevPlaceholder title="利用申请" description="档案利用申请审批流程" icon="heroicons:document-plus" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
