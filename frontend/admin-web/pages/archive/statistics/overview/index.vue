<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="综合统计"
      description="馆藏、数字化、鉴定、利用各维度实时统计分析"
      icon="heroicons:chart-pie"
    />

    <!-- 筛选 -->
    <div class="pro-card p-4 flex items-center gap-3">
      <NSelect
        v-model:value="fondsId"
        :options="fondsOptions"
        placeholder="全部全宗"
        clearable
        style="width: 240px"
        @update:value="load"
      />
      <NButton tertiary :loading="loading" @click="load">
        <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
        刷新
      </NButton>
    </div>

    <!-- KPI -->
    <div class="grid grid-cols-2 md:grid-cols-4 gap-4">
      <KpiCard label="馆藏总量" :value="fmt(data?.kpi.holdings_total)" sub="件（正式库）" icon="heroicons:archive-box" icon-bg="rgba(59,130,246,0.1)" icon-color="#3b82f6" />
      <KpiCard label="待整理" :value="fmt(data?.kpi.staging_pending)" sub="件（暂存库）" icon="heroicons:inbox" icon-bg="rgba(245,158,11,0.1)" icon-color="#f59e0b" />
      <KpiCard label="本年新增" :value="fmt(data?.kpi.year_new)" sub="件" icon="heroicons:plus-circle" icon-bg="rgba(16,185,129,0.1)" icon-color="#10b981" />
      <KpiCard label="本年利用" :value="fmt(data?.kpi.year_util_visits)" sub="人次" icon="heroicons:users" icon-bg="rgba(139,92,246,0.1)" icon-color="#8b5cf6" />
      <KpiCard label="数字化率" :value="data ? `${data.kpi.digitized_rate}%` : '—'" :sub="`已挂原文 ${fmt(data?.kpi.digitized_count)} 件`" icon="heroicons:document-check" icon-bg="rgba(6,182,212,0.1)" icon-color="#06b6d4" />
      <KpiCard label="数字化容量" :value="data ? `${data.kpi.capacity_gb}` : '—'" sub="GB" icon="heroicons:circle-stack" icon-bg="rgba(236,72,153,0.1)" icon-color="#ec4899" />
      <KpiCard label="开放率" :value="data ? `${data.kpi.open_rate}%` : '—'" :sub="`已开放 ${fmt(data?.kpi.opened_count)} 件`" icon="heroicons:lock-open" icon-bg="rgba(34,197,94,0.1)" icon-color="#22c55e" />
      <KpiCard label="全宗数量" :value="fmt(data?.kpi.fonds_count)" sub="个" icon="heroicons:building-library" icon-bg="rgba(100,116,139,0.1)" icon-color="#64748b" />
    </div>

    <!-- 图表区 -->
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-4">
      <ChartCard title="馆藏按年度分布">
        <EChart :option="barOption(charts.holdings_by_year, '#3b82f6')" :height="280" />
      </ChartCard>
      <ChartCard title="近 12 月新增归档趋势">
        <EChart :option="lineOption(charts.monthly_new, '#10b981')" :height="280" />
      </ChartCard>
      <ChartCard title="门类分布">
        <EChart :option="pieOption(charts.by_category)" :height="280" />
      </ChartCard>
      <ChartCard title="开放状态分布">
        <EChart :option="pieOption(charts.by_kfzt, KFZT_COLORS)" :height="280" />
      </ChartCard>
      <ChartCard title="保管期限分布">
        <EChart :option="pieOption(charts.by_bgqx)" :height="280" />
      </ChartCard>
      <ChartCard title="密级分布">
        <EChart :option="barOption(charts.by_mj, '#f59e0b')" :height="280" />
      </ChartCard>
      <ChartCard title="各全宗馆藏对比">
        <EChart :option="barOption(charts.by_fonds, '#8b5cf6')" :height="280" />
      </ChartCard>
      <ChartCard title="近 12 月利用趋势">
        <EChart :option="lineOption(charts.util_monthly, '#06b6d4')" :height="280" />
      </ChartCard>
      <ChartCard title="利用方式分布">
        <EChart :option="pieOption(charts.util_by_type)" :height="280" />
      </ChartCard>
    </div>
  </div>
</template>

<script setup lang="tsx">
import { computed, h, onMounted, ref } from "vue";
import { NButton, NSelect } from "naive-ui";
import { AdminPageHeader, KpiCard } from "@/components/admin";
import { EChart } from "@/components/ui";
import { StatisticsAPI } from "@/api/statistics";
import type { NameValue, OverviewData } from "@/api/statistics";
import { FondsAPI } from "@/api/repository";
import type { Fonds } from "@/api/repository";

definePageMeta({ layout: "archive", middleware: "auth" });

const KFZT_COLORS = ["#22c55e", "#f59e0b", "#3b82f6", "#ef4444", "#94a3b8"];

const loading = ref(false);
const data = ref<OverviewData | null>(null);
const fondsId = ref<string | null>(null);
const fondsOptions = ref<{ label: string; value: string }[]>([]);

const EMPTY: NameValue[] = [];
const charts = computed(() => data.value?.charts ?? {
  holdings_by_year: EMPTY, by_category: EMPTY, by_bgqx: EMPTY, by_mj: EMPTY,
  by_kfzt: EMPTY, by_fonds: EMPTY, monthly_new: EMPTY, util_by_type: EMPTY, util_monthly: EMPTY,
});

const ChartCard = (props: { title: string }, { slots }: { slots: { default?: () => unknown } }) =>
  h("div", { class: "pro-card p-4" }, [
    h("p", { class: "text-[13px] font-semibold mb-2", style: "color:var(--semi-color-text-0)" }, props.title),
    slots.default?.(),
  ]);

function fmt(v?: number): string {
  return v === undefined || v === null ? "—" : v.toLocaleString();
}

function barOption(rows: NameValue[], color: string): Record<string, unknown> {
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 50, right: 16, top: 24, bottom: 40 },
    xAxis: { type: "category", data: rows.map((r) => r.name), axisLabel: { rotate: rows.length > 8 ? 40 : 0 } },
    yAxis: { type: "value" },
    series: [{ type: "bar", data: rows.map((r) => r.value), itemStyle: { color, borderRadius: [4, 4, 0, 0] }, barMaxWidth: 36 }],
  };
}

function lineOption(rows: NameValue[], color: string): Record<string, unknown> {
  return {
    tooltip: { trigger: "axis" },
    grid: { left: 50, right: 16, top: 24, bottom: 40 },
    xAxis: { type: "category", data: rows.map((r) => r.name), boundaryGap: false },
    yAxis: { type: "value" },
    series: [{
      type: "line", data: rows.map((r) => r.value), smooth: true,
      itemStyle: { color }, lineStyle: { color, width: 2.5 },
      areaStyle: { color, opacity: 0.12 },
    }],
  };
}

function pieOption(rows: NameValue[], colors?: string[]): Record<string, unknown> {
  return {
    tooltip: { trigger: "item", formatter: "{b}: {c} ({d}%)" },
    legend: { bottom: 0, type: "scroll" },
    ...(colors ? { color: colors } : {}),
    series: [{
      type: "pie", radius: ["38%", "62%"], center: ["50%", "44%"],
      data: rows, label: { formatter: "{b}\n{c}" },
    }],
  };
}

async function load() {
  loading.value = true;
  try {
    const res = await StatisticsAPI.overview(fondsId.value ?? undefined);
    if (res.code === 0) data.value = res.data;
  } finally {
    loading.value = false;
  }
}

onMounted(async () => {
  load();
  const res = await FondsAPI.list();
  fondsOptions.value = (res.data ?? []).map((f: Fonds) => ({
    label: `${f.fonds_code} - ${f.short_name || f.name}`,
    value: f.id,
  }));
});
</script>
