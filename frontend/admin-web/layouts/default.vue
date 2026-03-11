<template>
  <div class="min-h-screen flex flex-col bg-[var(--semi-color-bg-1)]">
    <!-- 顶部固定 Header -->
    <AppHeader />

    <!-- 页面内容插槽，flex-1 撑满剩余高度 -->
    <div class="flex-1">
      <slot />
    </div>
  </div>
</template>

<script setup lang="ts">
import AppHeader from "@/components/layout/AppHeader.vue";
</script>
