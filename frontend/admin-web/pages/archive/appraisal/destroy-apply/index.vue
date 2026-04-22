<template>
  <DevPlaceholder title="销毁申请" description="到期档案销毁申请" icon="heroicons:trash" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
