<template>
  <div v-if="run" class="flex flex-col gap-4">
    <!-- 结论 + 雷达 -->
    <div class="flex gap-4">
      <div class="flex-1 rounded-xl border p-4 flex flex-col justify-center gap-2" :class="conclClass">
        <div class="flex items-center gap-2">
          <Icon :name="conclIcon" class="w-6 h-6" />
          <span class="text-lg font-bold">{{ CONCLUSION_LABEL[run.conclusion] }}</span>
        </div>
        <div class="text-3xl font-bold tabular-nums">{{ run.overall_score }}<span class="text-sm font-normal ml-1">分</span></div>
        <div class="text-xs flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
          <span class="text-green-600">通过 {{ run.passed }}</span>
          <span class="text-yellow-600">警告 {{ run.warned }}</span>
          <span class="text-red-600">不通过 {{ run.failed }}</span>
          <span class="text-blue-600">待办 {{ run.manual_pending }}</span>
        </div>
        <div class="text-[11px] text-gray-400 mt-1">{{ run.scheme_name }} · {{ run.target_label }}</div>
      </div>
      <EChart :option="radarOption" :height="200" style="width: 240px" />
    </div>

    <div class="flex items-center justify-between">
      <span class="text-sm font-medium">逐项结论（{{ run.results.length }} 项）</span>
      <NButton size="small" tertiary @click="printReport">
        <template #icon><Icon name="heroicons:printer" class="w-4 h-4" /></template>
        打印检测报告
      </NButton>
    </div>

    <!-- 逐项 -->
    <div class="flex flex-col gap-1.5">
      <div v-for="it in run.results" :key="it.id" class="rounded-lg border px-3 py-2" style="border-color:var(--semi-color-border)">
        <div class="flex items-center gap-2">
          <NTag size="tiny" :bordered="false">{{ DIM_LABEL[it.dimension] }}</NTag>
          <span class="text-[13px] font-medium" style="color:var(--semi-color-text-0)">{{ it.check_name }}</span>
          <NTag size="tiny" :type="EXEC_TONE[it.exec_type]" :bordered="false">{{ EXEC_LABEL[it.exec_type] }}</NTag>
          <NTag v-if="it.is_blocking" size="tiny" type="warning" :bordered="false">必检</NTag>
          <div class="flex-1" />
          <NTag size="small" :type="RESULT_TONE[it.result]" round>{{ RESULT_LABEL[it.result] }}</NTag>
        </div>
        <div class="flex items-center justify-between mt-1">
          <div class="text-[11.5px]" style="color:var(--semi-color-text-3)">
            <span v-if="it.standard_ref">{{ it.standard_ref }} · </span>{{ it.message }}
            <span v-if="it.confidence != null"> · 置信度 {{ (it.confidence * 100).toFixed(0) }}%</span>
          </div>
          <div v-if="it.result === 'manual_pending'" class="flex gap-1.5 shrink-0">
            <NButton size="tiny" type="success" tertiary @click="decide(it, 'pass')">通过</NButton>
            <NButton size="tiny" type="warning" tertiary @click="decide(it, 'warn')">警告</NButton>
            <NButton size="tiny" type="error" tertiary @click="decide(it, 'fail')">不通过</NButton>
          </div>
        </div>
      </div>
    </div>
  </div>
  <NSpin v-else size="small" />
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted } from "vue";
import { NTag, NButton, NSpin, useMessage } from "naive-ui";
import { EChart } from "@/components/ui";
import { PreservationAPI } from "@/api/preservation";
import type { RunDetail, ResultItem } from "@/api/preservation";

const props = defineProps<{ runId?: string | null }>();
const emit = defineEmits<{ changed: [] }>();
const message = useMessage();

const DIM_LABEL: Record<string, string> = { authenticity: "真实性", integrity: "完整性", usability: "可用性", safety: "安全性" };
const EXEC_LABEL: Record<string, string> = { rule: "规则", ai: "AI", manual: "人工" };
const EXEC_TONE: Record<string, "default" | "info" | "warning"> = { rule: "default", ai: "info", manual: "warning" };
const RESULT_LABEL: Record<string, string> = { pass: "通过", warn: "警告", fail: "不通过", skip: "不适用", manual_pending: "待办" };
const RESULT_TONE: Record<string, "success" | "warning" | "error" | "default" | "info"> = { pass: "success", warn: "warning", fail: "error", skip: "default", manual_pending: "info" };
const CONCLUSION_LABEL: Record<string, string> = { pass: "合格", warn: "基本合格", fail: "不合格", pending: "待复核" };

const run = ref<RunDetail | null>(null);

const conclClass = computed(() => {
  const c = run.value?.conclusion;
  return c === "pass" ? "border-green-200 bg-green-50 text-green-700"
    : c === "fail" ? "border-red-200 bg-red-50 text-red-700"
      : c === "warn" ? "border-yellow-200 bg-yellow-50 text-yellow-700"
        : "border-blue-200 bg-blue-50 text-blue-700";
});
const conclIcon = computed(() => {
  const c = run.value?.conclusion;
  return c === "pass" ? "heroicons:shield-check" : c === "fail" ? "heroicons:shield-exclamation" : c === "warn" ? "heroicons:exclamation-triangle" : "heroicons:clock";
});

const radarOption = computed(() => {
  const d = run.value?.dim_scores ?? {};
  const dims = ["authenticity", "integrity", "usability", "safety"];
  return {
    tooltip: {},
    radar: {
      indicator: dims.map((x) => ({ name: DIM_LABEL[x], max: 100 })),
      radius: "62%", splitNumber: 4,
      axisName: { color: "#64748b", fontSize: 11 },
      splitLine: { lineStyle: { color: "#e2e8f0" } },
      splitArea: { areaStyle: { color: ["#fff", "#f8fafc"] } },
    },
    series: [{
      type: "radar",
      data: [{ value: dims.map((x) => d[x] ?? 0), name: "四性得分", areaStyle: { color: "rgba(37,99,235,0.18)" }, lineStyle: { color: "#2563eb" }, itemStyle: { color: "#2563eb" } }],
    }],
  };
});

async function reload() {
  if (!props.runId) { run.value = null; return; }
  run.value = (await PreservationAPI.getRun(props.runId)).data;
}

async function decide(it: ResultItem, result: string) {
  if (!props.runId) return;
  await PreservationAPI.decide(props.runId, it.id, { result });
  message.success("已判定");
  await reload();
  emit("changed");
}

function printReport() {
  const r = run.value;
  if (!r) return;
  const w = window.open("", "_blank");
  if (!w) { message.warning("打印窗口被拦截"); return; }
  const esc = (v: string) => v.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const rows = r.results.map((it, i) => `<tr><td>${i + 1}</td><td>${DIM_LABEL[it.dimension]}</td><td>${esc(it.check_name)}</td><td>${esc(it.standard_ref || "")}</td><td>${RESULT_LABEL[it.result]}</td><td>${esc(it.message || "")}</td></tr>`).join("");
  const dims = ["authenticity", "integrity", "usability", "safety"].map((x) => `${DIM_LABEL[x]} ${(r.dim_scores ?? {})[x] ?? 0}`).join(" · ");
  w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>四性检测报告</title>
    <style>body{font-family:"Microsoft YaHei",sans-serif;padding:32px;color:#111}
    h1{text-align:center;font-size:20px;margin-bottom:4px}.meta{text-align:center;color:#555;font-size:13px;margin-bottom:16px}
    table{width:100%;border-collapse:collapse;font-size:12px}th,td{border:1px solid #999;padding:5px 8px;text-align:left}th{background:#f0f0f0}
    .concl{font-size:15px;margin:12px 0;font-weight:bold}</style></head><body>
    <h1>电子档案四性检测报告</h1>
    <div class="meta">对象：${esc(r.target_label || "")} ｜ 方案：${esc(r.scheme_name || "")} ｜ 检测时间：${new Date(r.finished_at || r.create_time).toLocaleString("zh-CN")}</div>
    <div class="concl">检测结论：${CONCLUSION_LABEL[r.conclusion]}（总分 ${r.overall_score}）&nbsp;&nbsp;维度：${dims}</div>
    <table><thead><tr><th>序号</th><th>维度</th><th>检测项</th><th>依据标准</th><th>结论</th><th>说明</th></tr></thead><tbody>${rows}</tbody></table>
    </body></html>`);
  w.document.close();
  w.focus();
  setTimeout(() => w.print(), 300);
}

watch(() => props.runId, reload);
onMounted(reload);
</script>
