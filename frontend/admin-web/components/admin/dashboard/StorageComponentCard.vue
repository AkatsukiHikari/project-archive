<template>
  <div class="comp-card" :class="{ 'comp-error': component.status === 'error' }">
    <!-- 头部：图标 + 名称 + 状态 + 延迟 -->
    <div class="comp-header">
      <div class="flex items-center gap-2.5">
        <div class="comp-icon-wrap" :style="`background: ${typeConfig.bg}`">
          <Icon :name="typeConfig.icon" class="w-4 h-4" :style="`color: ${typeConfig.color}`" />
        </div>
        <div>
          <p class="comp-name">{{ component.name }}</p>
          <p class="comp-summary">{{ component.summary }}</p>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <span class="latency" :class="latencyClass">{{ component.latency_ms }} ms</span>
        <span class="status-dot" :class="component.status === 'ok' ? 'dot-ok' : 'dot-err'" />
      </div>
    </div>

    <!-- 指标列表 -->
    <div class="comp-metrics">
      <div v-for="m in component.metrics" :key="m.label" class="metric-row">
        <span class="metric-label">{{ m.label }}</span>
        <span class="metric-value">{{ m.value }}</span>
      </div>
    </div>

    <!-- MinIO 专属：各桶用量柱状图 -->
    <div v-if="component.chart_data?.length" class="mt-3">
      <p class="text-[11px] mb-2" style="color: var(--semi-color-text-2)">存储桶用量分布</p>
      <div ref="chartEl" class="bucket-chart" />
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted, onUnmounted, nextTick } from "vue";
import * as echarts from "echarts/core";
import { BarChart } from "echarts/charts";
import { GridComponent, TooltipComponent } from "echarts/components";
import { CanvasRenderer } from "echarts/renderers";
import type { StorageComponent } from "@/api/iam";

echarts.use([BarChart, GridComponent, TooltipComponent, CanvasRenderer]);

const props = defineProps<{ component: StorageComponent }>();

// 各存储类型的视觉配置
const TYPE_CONFIG: Record<string, { icon: string; color: string; bg: string }> = {
  postgres:      { icon: "heroicons:circle-stack",       color: "#3b82f6", bg: "rgba(59,130,246,0.1)" },
  redis:         { icon: "heroicons:bolt",               color: "#ef4444", bg: "rgba(239,68,68,0.1)" },
  minio:         { icon: "heroicons:server-stack",       color: "#10b981", bg: "rgba(16,185,129,0.1)" },
  elasticsearch: { icon: "heroicons:magnifying-glass",   color: "#f59e0b", bg: "rgba(245,158,11,0.1)" },
  rabbitmq:      { icon: "heroicons:queue-list",         color: "#8b5cf6", bg: "rgba(139,92,246,0.1)" },
};

const DEFAULT_TYPE_CONFIG = { icon: "heroicons:circle-stack", color: "#3b82f6", bg: "rgba(59,130,246,0.1)" };
const typeConfig = computed(() => TYPE_CONFIG[props.component.type] ?? DEFAULT_TYPE_CONFIG);

const latencyClass = computed(() => {
  const ms = props.component.latency_ms;
  if (props.component.status === "error") return "latency-err";
  if (ms < 10)  return "latency-good";
  if (ms < 100) return "latency-warn";
  return "latency-slow";
});

// MinIO 桶用量柱状图
const chartEl = ref<HTMLElement | null>(null);
let chart: echarts.ECharts | null = null;

function renderBucketChart() {
  if (!chart || !props.component.chart_data?.length) return;
  const data = props.component.chart_data;
  chart.setOption({
    tooltip: {
      trigger: "axis",
      axisPointer: { type: "shadow" },
      formatter: (params: unknown) => {
        const p = (params as { name: string; value: number }[])[0];
        if (!p) return "";
        return `${p.name}<br/><b>${p.value} MB</b>`;
      },
      backgroundColor: "var(--semi-color-bg-0)",
      borderColor: "var(--semi-color-border)",
      textStyle: { color: "var(--semi-color-text-0)", fontSize: 11 },
    },
    grid: { top: 4, right: 8, bottom: 20, left: 8, containLabel: true },
    xAxis: {
      type: "category",
      data: data.map((b) => b.name),
      axisLabel: { color: "var(--semi-color-text-2)", fontSize: 10, rotate: data.length > 4 ? 30 : 0 },
      axisTick: { show: false },
      axisLine: { lineStyle: { color: "var(--semi-color-border)" } },
    },
    yAxis: {
      type: "value",
      axisLabel: { color: "var(--semi-color-text-2)", fontSize: 10, formatter: (v: number) => `${v}M` },
      splitLine: { lineStyle: { color: "var(--semi-color-fill-0)" } },
    },
    series: [{
      type: "bar",
      data: data.map((b) => b.size_mb),
      barMaxWidth: 32,
      itemStyle: {
        color: new echarts.graphic.LinearGradient(0, 0, 0, 1, [
          { offset: 0, color: "#10b981" },
          { offset: 1, color: "#34d399" },
        ]),
        borderRadius: [4, 4, 0, 0],
      },
    }],
  });
}

const resizeObserver = new ResizeObserver(() => chart?.resize());

onMounted(async () => {
  if (!props.component.chart_data?.length) return;
  await nextTick();
  if (chartEl.value) {
    chart = echarts.init(chartEl.value);
    resizeObserver.observe(chartEl.value);
    renderBucketChart();
  }
});

onUnmounted(() => {
  resizeObserver.disconnect();
  chart?.dispose();
});
</script>

<style scoped>
.comp-card {
  background: var(--semi-color-bg-0);
  border: 1px solid var(--semi-color-border);
  border-radius: 12px;
  padding: 16px;
  box-shadow: 0 1px 3px rgba(0,0,0,.04);
  transition: box-shadow 0.2s;
}
.comp-card:hover { box-shadow: 0 4px 12px rgba(0,0,0,.08); }
.comp-error { border-color: rgba(239,68,68,0.3); background: rgba(239,68,68,0.02); }

.comp-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  margin-bottom: 12px;
}
.comp-icon-wrap {
  width: 36px; height: 36px;
  border-radius: 8px;
  display: flex; align-items: center; justify-content: center;
  flex-shrink: 0;
}
.comp-name {
  font-size: 13px;
  font-weight: 600;
  color: var(--semi-color-text-0);
}
.comp-summary {
  font-size: 11px;
  color: var(--semi-color-text-2);
  margin-top: 1px;
  max-width: 240px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.comp-metrics {
  display: flex;
  flex-direction: column;
  gap: 4px;
}
.metric-row {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 5px 8px;
  border-radius: 6px;
  background: var(--semi-color-fill-0);
}
.metric-label {
  font-size: 12px;
  color: var(--semi-color-text-2);
}
.metric-value {
  font-size: 12px;
  font-weight: 500;
  color: var(--semi-color-text-0);
  font-variant-numeric: tabular-nums;
}

.status-dot {
  width: 8px; height: 8px;
  border-radius: 50%;
  flex-shrink: 0;
}
.dot-ok  { background: #22c55e; box-shadow: 0 0 5px rgba(34,197,94,.5); }
.dot-err { background: #ef4444; box-shadow: 0 0 5px rgba(239,68,68,.5); }

.latency { font-size: 11px; font-variant-numeric: tabular-nums; }
.latency-good { color: #22c55e; }
.latency-warn { color: #f59e0b; }
.latency-slow { color: #ef4444; }
.latency-err  { color: #ef4444; }

.bucket-chart { height: 100px; width: 100%; }
</style>
