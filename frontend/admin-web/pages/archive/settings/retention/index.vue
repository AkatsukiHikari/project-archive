<template>
  <DevPlaceholder title="保管期限表" description="配置档案保管期限标准表" icon="heroicons:calendar-days" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
