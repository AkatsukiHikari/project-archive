<template>
  <div class="flex-1 min-w-0">
    <NMenu
      mode="horizontal"
      responsive
      :options="options"
      :value="selectedKey"
      @update:value="(k: string) => emit('select', k)"
    />
  </div>
</template>

<script setup lang="ts">
import { NMenu, type MenuOption } from "naive-ui";

defineProps<{
  options: MenuOption[];
  selectedKey: string | null;
}>();

const emit = defineEmits<{ (e: "select", key: string): void }>();
</script>
