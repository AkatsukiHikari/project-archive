<template>
  <div class="min-h-screen w-full flex flex-col gap-4 p-5" style="background:#070d1f;color:#dbe4ff">
    <!-- 顶栏 -->
    <div class="flex items-center">
      <NuxtLink
        to="/archive/statistics/overview"
        class="text-[12px] flex items-center gap-1 no-underline"
        style="color:#5a6c9e"
      >
        <Icon name="heroicons:arrow-left" class="w-4 h-4" />退出大屏
      </NuxtLink>
      <div class="flex-1 text-center">
        <h1
          class="text-[26px] font-bold tracking-[0.3em] m-0"
          style="background:linear-gradient(90deg,#4f8fff,#37e2d5);-webkit-background-clip:text;background-clip:text;color:transparent"
        >
          档 案 数 据 驾 驶 舱
        </h1>
        <p class="text-[11px] mt-1" style="color:#5a6c9e">SMART ARCHIVE MANAGEMENT SYSTEM · 实时数据 {{ clock }}</p>
      </div>
      <button
        class="text-[12px] flex items-center gap-1 bg-transparent border rounded-md px-3 py-1.5 cursor-pointer"
        style="color:#7d93cf;border-color:#22305c"
        @click="toggleFullscreen"
      >
        <Icon name="heroicons:arrows-pointing-out" class="w-4 h-4" />全屏
      </button>
    </div>

    <!-- 核心指标带 -->
    <div class="grid grid-cols-3 md:grid-cols-6 gap-3">
      <div v-for="m in coreMetrics" :key="m.label" class="rounded-[10px] border border-[#1c2a55] bg-[linear-gradient(160deg,rgba(21,33,70,0.85),rgba(10,17,40,0.95))] shadow-[inset_0_0_24px_rgba(38,64,140,0.18)] flex flex-col items-center py-4">
        <span class="text-[12px]" style="color:#7d93cf">{{ m.label }}</span>
        <span class="text-[30px] font-bold tabular-nums leading-tight" :style="`color:${m.color}`">
          {{ m.value }}
        </span>
        <span class="text-[11px]" style="color:#5a6c9e">{{ m.unit }}</span>
      </div>
    </div>

    <!-- 三列图表 -->
    <div class="grid grid-cols-1 xl:grid-cols-3 gap-3 flex-1">
      <div class="flex flex-col gap-3">
        <div class="rounded-[10px] border border-[#1c2a55] bg-[linear-gradient(160deg,rgba(21,33,70,0.85),rgba(10,17,40,0.95))] shadow-[inset_0_0_24px_rgba(38,64,140,0.18)] p-3">
          <p class="m-0 mb-1 text-[12.5px] font-semibold text-[#9fb3e8] tracking-[0.08em] border-l-[3px] border-l-[#4f8fff] pl-2">馆藏按年度分布</p>
          <EChart :option="darkBar(charts.holdings_by_year, '#4f8fff')" :height="220" />
        </div>
        <div class="rounded-[10px] border border-[#1c2a55] bg-[linear-gradient(160deg,rgba(21,33,70,0.85),rgba(10,17,40,0.95))] shadow-[inset_0_0_24px_rgba(38,64,140,0.18)] p-3">
          <p class="m-0 mb-1 text-[12.5px] font-semibold text-[#9fb3e8] tracking-[0.08em] border-l-[3px] border-l-[#4f8fff] pl-2">保管期限分布</p>
          <EChart :option="darkPie(charts.by_bgqx)" :height="220" />
        </div>
      </div>

      <div class="flex flex-col gap-3">
        <div class="rounded-[10px] border border-[#1c2a55] bg-[linear-gradient(160deg,rgba(21,33,70,0.85),rgba(10,17,40,0.95))] shadow-[inset_0_0_24px_rgba(38,64,140,0.18)] p-3">
          <p class="m-0 mb-1 text-[12.5px] font-semibold text-[#9fb3e8] tracking-[0.08em] border-l-[3px] border-l-[#4f8fff] pl-2">开放鉴定状态</p>
          <EChart :option="darkPie(charts.by_kfzt, ['#37e2d5', '#ffb648', '#4f8fff', '#ff5d7a', '#46598f'])" :height="220" />
        </div>
        <div class="rounded-[10px] border border-[#1c2a55] bg-[linear-gradient(160deg,rgba(21,33,70,0.85),rgba(10,17,40,0.95))] shadow-[inset_0_0_24px_rgba(38,64,140,0.18)] p-3">
          <p class="m-0 mb-1 text-[12.5px] font-semibold text-[#9fb3e8] tracking-[0.08em] border-l-[3px] border-l-[#4f8fff] pl-2">今日动态</p>
          <div class="grid grid-cols-2 gap-3 py-3">
            <div v-for="d in dynamicMetrics" :key="d.label" class="flex flex-col items-center gap-1">
              <span class="text-[24px] font-bold tabular-nums" :style="`color:${d.color}`">{{ d.value }}</span>
              <span class="text-[11.5px]" style="color:#7d93cf">{{ d.label }}</span>
            </div>
          </div>
        </div>
      </div>

      <div class="flex flex-col gap-3">
        <div class="rounded-[10px] border border-[#1c2a55] bg-[linear-gradient(160deg,rgba(21,33,70,0.85),rgba(10,17,40,0.95))] shadow-[inset_0_0_24px_rgba(38,64,140,0.18)] p-3">
          <p class="m-0 mb-1 text-[12.5px] font-semibold text-[#9fb3e8] tracking-[0.08em] border-l-[3px] border-l-[#4f8fff] pl-2">各全宗馆藏</p>
          <EChart :option="darkBar(charts.by_fonds, '#9d6bff')" :height="220" />
        </div>
        <div class="rounded-[10px] border border-[#1c2a55] bg-[linear-gradient(160deg,rgba(21,33,70,0.85),rgba(10,17,40,0.95))] shadow-[inset_0_0_24px_rgba(38,64,140,0.18)] p-3">
          <p class="m-0 mb-1 text-[12.5px] font-semibold text-[#9fb3e8] tracking-[0.08em] border-l-[3px] border-l-[#4f8fff] pl-2">近 12 月利用趋势</p>
          <EChart :option="darkLine(charts.util_monthly, '#37e2d5')" :height="220" />
        </div>
      </div>
    </div>

    <div class="grid grid-cols-1 xl:grid-cols-2 gap-3">
      <div class="rounded-[10px] border border-[#1c2a55] bg-[linear-gradient(160deg,rgba(21,33,70,0.85),rgba(10,17,40,0.95))] shadow-[inset_0_0_24px_rgba(38,64,140,0.18)] p-3">
        <p class="m-0 mb-1 text-[12.5px] font-semibold text-[#9fb3e8] tracking-[0.08em] border-l-[3px] border-l-[#4f8fff] pl-2">门类分布</p>
        <EChart :option="darkBar(charts.by_category, '#ffb648')" :height="190" />
      </div>
      <div class="rounded-[10px] border border-[#1c2a55] bg-[linear-gradient(160deg,rgba(21,33,70,0.85),rgba(10,17,40,0.95))] shadow-[inset_0_0_24px_rgba(38,64,140,0.18)] p-3 flex flex-col justify-center items-center gap-2">
        <p class="m-0 mb-1 self-start text-[12.5px] font-semibold text-[#9fb3e8] tracking-[0.08em] border-l-[3px] border-l-[#4f8fff] pl-2">数字化进度</p>
        <div class="w-full px-6">
          <div class="flex justify-between text-[12px] mb-1" style="color:#7d93cf">
            <span>馆藏数字化率</span>
            <span style="color:#37e2d5">{{ data?.kpi.digitized_rate ?? 0 }}%</span>
          </div>
          <div class="h-3 rounded-full overflow-hidden" style="background:#13204a">
            <div
              class="h-full rounded-full transition-all duration-1000"
              :style="`width:${data?.kpi.digitized_rate ?? 0}%;background:linear-gradient(90deg,#4f8fff,#37e2d5)`"
            />
          </div>
          <p class="text-[11px] mt-2" style="color:#5a6c9e">
            已挂接数字化成果 {{ data?.kpi.digitized_count ?? 0 }} 件 · 容量 {{ data?.kpi.capacity_gb ?? 0 }} GB
          </p>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onBeforeUnmount, onMounted, ref } from "vue";
import { EChart } from "@/components/ui";
import { StatisticsAPI } from "@/api/statistics";
import type { CockpitData, NameValue } from "@/api/statistics";

definePageMeta({ layout: false, middleware: "auth" });

const REFRESH_MS = 30_000;
const data = ref<CockpitData | null>(null);
const clock = ref("");
let refreshTimer: ReturnType<typeof setInterval> | null = null;
let clockTimer: ReturnType<typeof setInterval> | null = null;

const EMPTY: NameValue[] = [];
const charts = computed(() => data.value?.charts ?? {
  holdings_by_year: EMPTY, by_category: EMPTY, by_kfzt: EMPTY,
  by_fonds: EMPTY, util_monthly: EMPTY, by_bgqx: EMPTY,
});

const coreMetrics = computed(() => {
  const k = data.value?.kpi;
  return [
    { label: "馆藏总量", value: k ? k.holdings_total.toLocaleString() : "—", unit: "件", color: "#4f8fff" },
    { label: "全宗数量", value: k ? String(k.fonds_count) : "—", unit: "个", color: "#9d6bff" },
    { label: "本年新增", value: k ? k.year_new.toLocaleString() : "—", unit: "件", color: "#37e2d5" },
    { label: "本年利用", value: k ? k.year_util_visits.toLocaleString() : "—", unit: "人次", color: "#ffb648" },
    { label: "数字化率", value: k ? `${k.digitized_rate}` : "—", unit: "%", color: "#37e2d5" },
    { label: "开放率", value: k ? `${k.open_rate}` : "—", unit: "%", color: "#4ade80" },
  ];
});

const dynamicMetrics = computed(() => {
  const d = data.value?.dynamic;
  return [
    { label: "今日利用", value: d ? String(d.today_util) : "—", color: "#37e2d5" },
    { label: "在途移交", value: d ? String(d.transit_transfers) : "—", color: "#ffb648" },
    { label: "进行中鉴定任务", value: d ? String(d.active_appraisal_tasks) : "—", color: "#4f8fff" },
    { label: "四性检测合格率", value: d?.detection_pass_rate != null ? `${d.detection_pass_rate}%` : "—", color: "#4ade80" },
  ];
});

const DARK_AXIS = {
  axisLine: { lineStyle: { color: "#22305c" } },
  axisLabel: { color: "#7d93cf" },
  splitLine: { lineStyle: { color: "#13204a" } },
};

function darkBar(rows: NameValue[], color: string): Record<string, unknown> {
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 44, right: 12, top: 16, bottom: 36 },
    xAxis: { type: "category", data: rows.map((r) => r.name), ...DARK_AXIS, axisLabel: { color: "#7d93cf", rotate: rows.length > 8 ? 40 : 0 } },
    yAxis: { type: "value", ...DARK_AXIS },
    series: [{ type: "bar", data: rows.map((r) => r.value), itemStyle: { color, borderRadius: [3, 3, 0, 0] }, barMaxWidth: 26 }],
  };
}

function darkLine(rows: NameValue[], color: string): Record<string, unknown> {
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 44, right: 12, top: 16, bottom: 36 },
    xAxis: { type: "category", data: rows.map((r) => r.name), boundaryGap: false, ...DARK_AXIS },
    yAxis: { type: "value", ...DARK_AXIS },
    series: [{
      type: "line", data: rows.map((r) => r.value), smooth: true,
      itemStyle: { color }, lineStyle: { color, width: 2.5 },
      areaStyle: { color, opacity: 0.18 },
    }],
  };
}

function darkPie(rows: NameValue[], colors?: string[]): Record<string, unknown> {
  return {
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: { bottom: 0, textStyle: { color: "#7d93cf" }, type: "scroll" },
    ...(colors ? { color: colors } : {}),
    series: [{
      type: "pie", radius: ["40%", "64%"], center: ["50%", "44%"],
      data: rows,
      label: { color: "#9fb3e8", formatter: "{b} {c}" },
      itemStyle: { borderColor: "#070d1f", borderWidth: 2 },
    }],
  };
}

async function load() {
  const res = await StatisticsAPI.cockpit();
  if (res.code === 0) data.value = res.data;
}

function toggleFullscreen() {
  if (document.fullscreenElement) document.exitFullscreen();
  else document.documentElement.requestFullscreen();
}

onMounted(() => {
  load();
  refreshTimer = setInterval(load, REFRESH_MS);
  clockTimer = setInterval(() => {
    clock.value = new Date().toLocaleString("zh-CN", { hour12: false });
  }, 1000);
});

onBeforeUnmount(() => {
  if (refreshTimer) clearInterval(refreshTimer);
  if (clockTimer) clearInterval(clockTimer);
});
</script>
