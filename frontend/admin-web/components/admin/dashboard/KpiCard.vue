<template>
  <div class="kpi-card">
    <div class="flex items-start justify-between">
      <div class="min-w-0 flex-1">
        <p class="kpi-label">{{ label }}</p>
        <div class="flex items-end gap-2 mt-1.5">
          <span class="kpi-value">{{ displayValue }}</span>
          <span v-if="sub" class="kpi-sub">{{ sub }}</span>
        </div>
        <div v-if="badge" class="mt-2 flex items-center gap-1">
          <span
            class="inline-flex items-center gap-1 text-[11px] font-medium px-1.5 py-0.5 rounded-full"
            :class="badgeClass"
          >
            <Icon :name="badgeIcon" class="w-3 h-3" />
            {{ badge }}
          </span>
        </div>
      </div>
      <div class="kpi-icon-wrap" :style="`background: ${iconBg}`">
        <Icon :name="icon" class="w-5 h-5" :style="`color: ${iconColor}`" />
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

const props = defineProps<{
  label: string;
  value: number | string;
  sub?: string;
  badge?: string;
  badgeType?: "up" | "down" | "warn";
  icon: string;
  iconBg?: string;
  iconColor?: string;
  loading?: boolean;
}>();

const displayValue = computed(() => {
  if (props.loading) return "—";
  if (typeof props.value === "number" && props.value < 0) return "—";
  return props.value;
});

const badgeClass = computed(() => {
  if (props.badgeType === "up") return "bg-green-100 text-green-700";
  if (props.badgeType === "down") return "bg-red-100 text-red-700";
  return "bg-yellow-100 text-yellow-700";
});

const badgeIcon = computed(() => {
  if (props.badgeType === "up") return "heroicons:arrow-trending-up";
  if (props.badgeType === "down") return "heroicons:arrow-trending-down";
  return "heroicons:exclamation-triangle";
});
</script>

<style scoped>
.kpi-card {
  background: var(--semi-color-bg-0);
  border: 1px solid var(--semi-color-border);
  border-radius: 12px;
  padding: 20px;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
  transition: box-shadow 0.2s;
}
.kpi-card:hover {
  box-shadow: 0 4px 12px rgba(0,0,0,.08);
}
.kpi-label {
  font-size: 11px;
  font-weight: 600;
  letter-spacing: 0.06em;
  text-transform: uppercase;
  color: var(--semi-color-text-2);
}
.kpi-value {
  font-size: 28px;
  font-weight: 700;
  color: var(--semi-color-text-0);
  line-height: 1;
}
.kpi-sub {
  font-size: 12px;
  color: var(--semi-color-text-2);
  padding-bottom: 2px;
}
.kpi-icon-wrap {
  width: 44px;
  height: 44px;
  border-radius: 10px;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}
</style>
