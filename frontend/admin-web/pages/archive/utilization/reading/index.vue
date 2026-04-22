<template>
  <DevPlaceholder title="查阅登记" description="来档查阅人员及查阅内容登记" icon="heroicons:eye" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
