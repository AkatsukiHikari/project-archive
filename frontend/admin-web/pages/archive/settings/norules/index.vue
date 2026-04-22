<template>
  <DevPlaceholder title="档号规则" description="配置档号自动生成规则" icon="heroicons:hashtag" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
