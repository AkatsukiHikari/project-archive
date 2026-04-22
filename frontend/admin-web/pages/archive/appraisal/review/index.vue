<template>
  <DevPlaceholder title="期限复查" description="保管期限届满档案的复查工作" icon="heroicons:clock" />
</template>

<script setup lang="ts">
import DevPlaceholder from "@/components/archive/DevPlaceholder.vue";
definePageMeta({ layout: "archive", middleware: "auth" });
</script>
