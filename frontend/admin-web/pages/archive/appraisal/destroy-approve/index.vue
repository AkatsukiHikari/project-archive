<template>
  <DevPlaceholder title="销毁审批" description="销毁申请审批及监督" icon="heroicons:check-badge" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
