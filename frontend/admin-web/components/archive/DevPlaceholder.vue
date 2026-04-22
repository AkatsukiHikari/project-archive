<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader :title="title" :description="description" :icon="icon" />
    <div
      class="flex flex-col items-center justify-center py-20 rounded-xl border-2 border-dashed"
      style="border-color: var(--semi-color-border); background: var(--semi-color-bg-0)"
    >
      <Icon name="heroicons:wrench-screwdriver" class="w-12 h-12 mb-4" style="color: var(--semi-color-text-3)" />
      <p class="text-base font-medium" style="color: var(--semi-color-text-1)">功能开发中</p>
      <p class="text-sm mt-1" style="color: var(--semi-color-text-3)">该功能正在建设中，敬请期待</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import AdminPageHeader from "@/components/admin/PageHeader.vue";

defineProps<{
  title: string;
  description?: string;
  icon?: string;
}>();
</script>
