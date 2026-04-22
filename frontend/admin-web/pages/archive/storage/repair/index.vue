<template>
  <DevPlaceholder title="档案修复" description="破损档案修复申请与记录" icon="heroicons:wrench-screwdriver" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
