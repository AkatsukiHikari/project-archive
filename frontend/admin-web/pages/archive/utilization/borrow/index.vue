<template>
  <DevPlaceholder title="借阅管理" description="档案借阅申请归还及催还管理" icon="heroicons:arrow-uturn-right" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
