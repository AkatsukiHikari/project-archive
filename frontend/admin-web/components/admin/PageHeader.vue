<template>
  <div class="flex items-center justify-between mb-6">
    <div class="flex items-center gap-3">
      <div
        v-if="icon"
        class="w-9 h-9 rounded-xl flex items-center justify-center shrink-0"
        style="background: var(--semi-color-primary-light-default)"
      >
        <Icon :name="icon" class="w-5 h-5" style="color: var(--semi-color-primary)" />
      </div>
      <div>
        <h1
          class="text-[15px] font-semibold leading-tight"
          style="color: var(--semi-color-text-0)"
        >
          {{ title }}
        </h1>
        <p
          v-if="description"
          class="text-xs mt-0.5 leading-relaxed"
          style="color: var(--semi-color-text-2)"
        >
          {{ description }}
        </p>
      </div>
    </div>
    <slot />
  </div>
</template>

<script setup lang="ts">
defineProps<{
  title: string;
  description?: string;
  icon?: string;
}>();
</script>
