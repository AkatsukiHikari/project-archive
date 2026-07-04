<template>
  <div ref="el" :style="{ width: '100%', height: `${height}px` }" />
</template>

<script setup lang="ts">
import { ref, watch, onMounted, onUnmounted, nextTick } from "vue";
import * as echarts from "echarts/core";
import { BarChart, PieChart, LineChart, RadarChart } from "echarts/charts";
import { GridComponent, TooltipComponent, LegendComponent, TitleComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";

echarts.use([BarChart, PieChart, LineChart, RadarChart, GridComponent, TooltipComponent, LegendComponent, TitleComponent, CanvasRenderer]);

const props = withDefaults(defineProps<{ option: Record<string, unknown>; height?: number }>(), {
  height: 260,
});
const emit = defineEmits<{ chartClick: [params: { name: string; dataIndex: number }] }>();

const el = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;

function render() {
  if (!chart || !el.value) return;
  chart.setOption(props.option as echarts.EChartsCoreOption, true);
}
function onResize() { chart?.resize(); }

onMounted(async () => {
  await nextTick();
  if (!el.value) return;
  chart = echarts.init(el.value);
  chart.on("click", (p) => emit("chartClick", { name: (p as { name: string }).name, dataIndex: (p as { dataIndex: number }).dataIndex }));
  render();
  window.addEventListener("resize", onResize);
});

watch(() => props.option, render, { deep: true });

onUnmounted(() => {
  window.removeEventListener("resize", onResize);
  chart?.dispose();
  chart = null;
});
</script>
