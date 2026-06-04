<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="AI 评测中心"
      description="黄金集准确率趋势 / 阈值门禁 / 驳回学习池，确保模型升级不回归"
      icon="heroicons:chart-bar"
    />

    <!-- 上线门禁状态 -->
    <div class="grid grid-cols-1 md:grid-cols-3 gap-3">
      <div
        v-for="card in summaryCards"
        :key="card.title"
        class="rounded-xl p-4 flex items-start gap-3"
        style="background:var(--semi-color-bg-0);border:1px solid var(--semi-color-border)"
      >
        <div
          class="w-10 h-10 rounded-lg flex items-center justify-center flex-shrink-0"
          :style="{ background: `${card.color}/0.12`, color: card.color }"
        >
          <Icon :name="card.icon" class="w-5 h-5" />
        </div>
        <div class="flex flex-col">
          <span class="text-[12px]" style="color:var(--semi-color-text-3)">{{ card.title }}</span>
          <span class="text-[18px] font-semibold leading-tight" style="color:var(--semi-color-text-0)">{{ card.value }}</span>
          <span class="text-[11px] mt-0.5" style="color:var(--semi-color-text-2)">{{ card.hint }}</span>
        </div>
      </div>
    </div>

    <ProTable
      :columns="columns"
      :data="runs"
      :loading="loading"
      empty-content="暂无评测记录（P2 起：每次 Workflow / 模型变更自动触发）"
    >
      <template #toolbar-left>
        <NSelect
          v-model:value="scenarioFilter"
          :options="SCENARIO_OPTIONS"
          class="w-40"
          placeholder="场景"
          clearable
          @update:value="reload"
        />
      </template>
      <template #toolbar-right>
        <NTag :bordered="false" type="info" size="small">
          <template #icon><Icon name="heroicons:information-circle" class="w-3.5 h-3.5" /></template>
          黄金集驳回学习池 P3 起开放
        </NTag>
      </template>
    </ProTable>
  </div>
</template>

<script setup lang="tsx">
import { computed, onMounted, ref } from "vue";
import { NSelect, NTag } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { listEvalRuns, listGolden, type EvalRunListItem } from "@/api/ai_admin";

definePageMeta({ layout: "admin", middleware: "auth" });

const SCENARIO_OPTIONS = [
  { label: "智能问答", value: "qa" },
  { label: "自然语言检索", value: "search" },
  { label: "档案摘要", value: "summary" },
  { label: "自动挂接", value: "attach" },
  { label: "自动编目", value: "catalog" },
];

const runs = ref<EvalRunListItem[]>([]);
const goldenTotal = ref(0);
const loading = ref(false);
const scenarioFilter = ref<string | null>(null);

const summaryCards = computed(() => [
  {
    title: "评测运行次数",
    value: runs.value.length || "—",
    hint: "本租户累计",
    icon: "heroicons:play-circle",
    color: "oklch(var(--p))",
  },
  {
    title: "黄金集条目",
    value: goldenTotal.value || "—",
    hint: "标注 + 种子 + 驳回入池",
    icon: "heroicons:rectangle-stack",
    color: "oklch(0.6 0.2 290)",
  },
  {
    title: "门禁阻断次数",
    value: runs.value.filter((r) => r.blocked_upgrade).length || 0,
    hint: "评测不达标自动回退",
    icon: "heroicons:shield-exclamation",
    color: "oklch(0.65 0.2 30)",
  },
]);

const columns = computed(() => [
  { title: "场景", key: "scenario_code", width: 110 },
  { title: "Workflow 版本", key: "workflow_version", width: 140 },
  { title: "模型档位", key: "model_tier", width: 90 },
  {
    title: "通过率",
    key: "passed",
    width: 110,
    render: (row: EvalRunListItem) => {
      if (row.total == null || row.passed == null || row.total === 0) return "—";
      return `${row.passed} / ${row.total} (${((row.passed / row.total) * 100).toFixed(1)}%)`;
    },
  },
  {
    title: "门禁",
    key: "blocked_upgrade",
    width: 90,
    render: (row: EvalRunListItem) =>
      row.blocked_upgrade ? (
        <NTag size="small" type="error" bordered={false}>已阻断</NTag>
      ) : (
        <NTag size="small" type="success" bordered={false}>放行</NTag>
      ),
  },
  { title: "状态", key: "status", width: 80 },
  {
    title: "运行时间",
    key: "create_time",
    width: 160,
    render: (row: EvalRunListItem) => new Date(row.create_time).toLocaleString("zh-CN"),
  },
]);

const reload = async () => {
  loading.value = true;
  try {
    const [runsRes, goldenRes] = await Promise.all([
      listEvalRuns({ scenario_code: scenarioFilter.value ?? undefined, size: 50 }),
      listGolden({ scenario_code: scenarioFilter.value ?? undefined, size: 1 }),
    ]);
    runs.value = runsRes.data.items;
    goldenTotal.value = goldenRes.data.total;
  } finally {
    loading.value = false;
  }
};

onMounted(() => reload());
</script>
