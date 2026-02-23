<template>
  <div :data-theme="currentTheme">
    <NuxtLayout>
      <NuxtPage />
    </NuxtLayout>
    <Toaster position="top-right" rich-colors />
  </div>
</template>

<script setup lang="ts">
import { Toaster } from "vue-sonner";
import { useTheme } from "@/hooks/useTheme";

const { currentTheme, initTheme } = useTheme();

onMounted(() => {
  initTheme();
});
</script>
