<template>
  <DevPlaceholder title="接收登记" description="正式登记接收档案，生成接收凭证" icon="heroicons:clipboard-document-check" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
