<template>
  <h2 class="text-xl font-bold text-base-content flex items-center gap-2">
    <span class="w-1.5 h-6 bg-primary rounded-full"></span>
    {{ title }}
  </h2>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
}>();
</script>
