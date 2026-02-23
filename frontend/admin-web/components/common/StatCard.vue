<template>
  <div class="bg-base-100 rounded-xl p-6 shadow-card border border-base-300">
    <div class="flex justify-between items-start mb-4">
      <div>
        <p class="text-base-content/60 text-sm font-medium mb-1">
          {{ label }}
        </p>
        <h3 class="text-3xl font-bold text-base-content font-display">
          {{ prefix }}{{ value }}
        </h3>
      </div>
      <div class="p-2 rounded-lg" :class="iconBgClass">
        <Icon :name="icon" class="w-5 h-5" />
      </div>
    </div>
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  label: string;
  value: string | number;
  prefix?: string;
  icon: string;
  iconBgClass?: string;
}>();
</script>
