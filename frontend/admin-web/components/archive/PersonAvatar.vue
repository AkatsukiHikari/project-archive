<template>
  <div
    class="rounded-full flex items-center justify-center font-semibold select-none overflow-hidden shrink-0"
    :style="{ width: `${size}px`, height: `${size}px`, fontSize: `${Math.round(size * 0.42)}px`, background: bg, color: '#fff' }"
    :title="name"
  >
    <img v-if="src" :src="src" class="w-full h-full object-cover" :alt="name">
    <span v-else>{{ initial }}</span>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = withDefaults(defineProps<{ name?: string; src?: string | null; size?: number }>(), {
  name: "",
  src: null,
  size: 36,
});

const initial = computed(() => (props.name?.trim()?.[0] ?? "?").toUpperCase());

// 从姓名稳定派生一个柔和的色相
const PALETTE = ["#2563eb", "#7c3aed", "#0891b2", "#059669", "#d97706", "#db2777", "#dc2626", "#4f46e5"];
const bg = computed(() => {
  const n = props.name || "?";
  let h = 0;
  for (let i = 0; i < n.length; i++) h = (h * 31 + n.charCodeAt(i)) & 0xffff;
  return PALETTE[h % PALETTE.length];
});
</script>
