<template>
  <div v-if="result" class="flex flex-col gap-4">
    <!-- 总分闸门 -->
    <div class="flex items-center gap-4 rounded-lg border p-4" :class="passClass">
      <div class="flex flex-col items-center justify-center min-w-[88px]">
        <span class="text-3xl font-bold tabular-nums" :class="scoreColor">{{ result.score.toFixed(1) }}</span>
        <span class="text-xs text-gray-500 mt-0.5">四性总分</span>
      </div>
      <div class="flex-1">
        <div class="flex items-center gap-2">
          <NTag :type="result.passed ? 'success' : 'error'" size="small" round>
            <template #icon>
              <Icon :name="result.passed ? 'heroicons:shield-check' : 'heroicons:shield-exclamation'" class="w-3.5 h-3.5" />
            </template>
            {{ result.passed ? "通过闸门" : "未通过闸门" }}
          </NTag>
          <span class="text-xs text-gray-500">闸门阈值 {{ result.threshold }} 分</span>
        </div>
        <div class="mt-2 flex flex-wrap gap-3 text-xs text-gray-600">
          <span>共 <strong>{{ result.total }}</strong> 件</span>
          <span class="text-green-600">合格 {{ result.ok }}</span>
          <span class="text-yellow-600">警告 {{ result.warning }}</span>
          <span class="text-red-600">错误 {{ result.error }}</span>
        </div>
      </div>
    </div>

    <!-- 四性维度 -->
    <div class="grid grid-cols-1 sm:grid-cols-2 gap-3">
      <div v-for="d in result.dimensions" :key="d.key" class="rounded-lg border p-3">
        <div class="flex items-center justify-between mb-1.5">
          <span class="text-sm font-medium">{{ d.label }}</span>
          <span class="text-sm font-semibold tabular-nums" :class="dimColor(d.score)">{{ d.score.toFixed(0) }}</span>
        </div>
        <NProgress
          type="line"
          :percentage="d.score"
          :height="6"
          :show-indicator="false"
          :status="d.score >= 80 ? 'success' : d.score >= 60 ? 'warning' : 'error'"
        />
        <ul v-if="d.issues.length" class="mt-2 flex flex-col gap-0.5">
          <li v-for="(iss, i) in d.issues" :key="i" class="text-xs text-red-500 flex items-start gap-1">
            <Icon name="heroicons:exclamation-triangle" class="w-3.5 h-3.5 mt-0.5 shrink-0" />
            <span>{{ iss }}</span>
          </li>
        </ul>
      </div>
    </div>

    <!-- 逐条问题（仅展示有问题的） -->
    <div v-if="problemEntries.length" class="rounded-lg border p-3">
      <p class="text-sm font-medium mb-2">问题明细（{{ problemEntries.length }} 条）</p>
      <div class="max-h-52 overflow-y-auto flex flex-col gap-1.5">
        <div
          v-for="e in problemEntries"
          :key="e.row_no"
          class="flex items-start gap-2 text-xs"
        >
          <NTag :type="e.status === 'error' ? 'error' : 'warning'" size="tiny">第 {{ e.row_no }} 条</NTag>
          <span class="text-gray-600">{{ e.issues.join("；") }}</span>
        </div>
      </div>
    </div>
  </div>
  <div v-else class="py-10 text-center text-sm text-gray-400">暂无预检结果</div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { NTag, NProgress } from "naive-ui";
import type { PrecheckResponse } from "@/api/collection";

const props = defineProps<{ result: PrecheckResponse | null }>();

const problemEntries = computed(() =>
  (props.result?.entries ?? []).filter((e) => e.status !== "ok"),
);

const passClass = computed(() =>
  props.result?.passed ? "border-green-200 bg-green-50" : "border-red-200 bg-red-50",
);

const scoreColor = computed(() => {
  const s = props.result?.score ?? 0;
  return s >= 80 ? "text-green-600" : s >= 60 ? "text-yellow-600" : "text-red-600";
});

function dimColor(score: number): string {
  return score >= 80 ? "text-green-600" : score >= 60 ? "text-yellow-600" : "text-red-600";
}
</script>
