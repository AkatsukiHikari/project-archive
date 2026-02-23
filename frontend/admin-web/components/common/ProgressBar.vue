<template>
  <div>
    <div
      v-if="showLabel"
      class="flex justify-between text-xs text-base-content/60 mb-1.5"
    >
      <span>{{ label }}</span>
      <span class="font-bold">{{ displayValue }}</span>
    </div>
    <div class="w-full bg-base-300 rounded-full" :class="trackHeight">
      <div
        class="rounded-full transition-all duration-500 relative overflow-hidden"
        :class="[barColor, trackHeight]"
        :style="{ width: `${percent}%` }"
      >
        <div
          v-if="animate"
          class="absolute top-0 left-0 bottom-0 right-0 w-full h-full bg-gradient-to-r from-transparent via-white/30 to-transparent -translate-x-full animate-[shimmer_2s_infinite]"
        />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
const props = defineProps<{
  percent: number;
  label?: string;
  barColor?: string;
  height?: "sm" | "md";
  animate?: boolean;
}>();

const showLabel = computed(() => !!props.label);
const displayValue = computed(() => `${props.percent}%`);
const trackHeight = computed(() => (props.height === "sm" ? "h-1.5" : "h-2"));
const barColor = computed(() => props.barColor || "bg-primary");
</script>
