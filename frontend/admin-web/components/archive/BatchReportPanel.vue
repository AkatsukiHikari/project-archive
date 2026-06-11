<template>
  <div v-if="batch" class="flex flex-col gap-4">
    <!-- 批次汇总 + 雷达 -->
    <div class="flex gap-4">
      <div class="flex-1 rounded-xl border p-4 flex flex-col gap-2" :class="conclClass">
        <div class="flex items-center gap-2">
          <Icon :name="conclIcon" class="w-6 h-6" />
          <span class="text-lg font-bold">{{ CONCLUSION_LABEL[batch.conclusion] }}</span>
          <span class="text-[12px] font-mono ml-1" style="opacity:.7">{{ batch.batch_no }}</span>
        </div>
        <div class="text-3xl font-bold tabular-nums">{{ batch.avg_score }}<span class="text-sm font-normal ml-1">平均分</span></div>
        <div class="text-xs flex flex-wrap gap-x-3 gap-y-0.5 mt-1">
          <span>共 {{ batch.total }} 件</span>
          <span class="text-green-600">合格 {{ batch.passed }}</span>
          <span class="text-yellow-600">基本合格 {{ batch.warned }}</span>
          <span class="text-red-600">不合格 {{ batch.failed }}</span>
          <span class="text-blue-600">待复核 {{ batch.pending }}</span>
        </div>
        <div class="text-xs mt-1"><span class="text-gray-400">检测范围：</span><span class="font-medium">{{ scopeText }}</span></div>
        <div class="text-[11px] text-gray-400">{{ batch.scheme_name }} · {{ fmt(batch.finished_at) }}</div>
      </div>
      <EChart :option="radarOption" :height="200" style="width: 240px" />
    </div>

    <div class="flex items-center justify-between">
      <span class="text-sm font-medium">逐件结果（{{ batch.runs.length }} 件，点行看单件报告）</span>
      <NButton size="small" tertiary @click="printBatch">
        <template #icon><Icon name="heroicons:printer" class="w-4 h-4" /></template>
        打印批次报告
      </NButton>
    </div>

    <ProTable :columns="columns" :data="batch.runs" :page-size="20" size="small" />
  </div>
  <NSpin v-else size="small" />
</template>

<script setup lang="tsx">
import { ref, computed, watch, onMounted, h } from "vue";
import { NButton, NSpin, NTag } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { ProTable, EChart } from "@/components/ui";
import { PreservationAPI } from "@/api/preservation";
import type { BatchDetail, Run } from "@/api/preservation";

const props = defineProps<{ batchId?: string | null }>();
const emit = defineEmits<{ openRun: [runId: string] }>();

const DIM_LABEL: Record<string, string> = { authenticity: "真实性", integrity: "完整性", usability: "可用性", safety: "安全性" };
const CONCLUSION_LABEL: Record<string, string> = { pass: "全部合格", warn: "基本合格", fail: "含不合格", pending: "含待复核" };
const RUN_CONCL_LABEL: Record<string, string> = { pass: "合格", warn: "基本合格", fail: "不合格", pending: "待复核" };
const RUN_TONE: Record<string, "success" | "warning" | "error" | "info"> = { pass: "success", warn: "warning", fail: "error", pending: "info" };

const batch = ref<BatchDetail | null>(null);
const fmt = (s?: string | null) => (s ? s.replace("T", " ").slice(0, 16) : "—");
const scopeText = computed(() => {
  const b = batch.value;
  if (!b) return "—";
  return b.scope_type === "single" ? `单件 · ${b.scope_label || "—"}` : b.scope_label || "—";
});

const conclClass = computed(() => {
  const c = batch.value?.conclusion;
  return c === "pass" ? "border-green-200 bg-green-50 text-green-700"
    : c === "fail" ? "border-red-200 bg-red-50 text-red-700"
      : c === "warn" ? "border-yellow-200 bg-yellow-50 text-yellow-700"
        : "border-blue-200 bg-blue-50 text-blue-700";
});
const conclIcon = computed(() => {
  const c = batch.value?.conclusion;
  return c === "pass" ? "heroicons:shield-check" : c === "fail" ? "heroicons:shield-exclamation" : c === "warn" ? "heroicons:exclamation-triangle" : "heroicons:clock";
});

const radarOption = computed(() => {
  const d = batch.value?.dim_scores ?? {};
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
    series: [{ type: "radar", data: [{ value: dims.map((x) => d[x] ?? 0), areaStyle: { color: "rgba(37,99,235,0.18)" }, lineStyle: { color: "#2563eb" }, itemStyle: { color: "#2563eb" } }] }],
  };
});

const columns: DataTableColumns<Run> = [
  { title: "序号", key: "_idx", width: 56, render: (_r, i) => i + 1 },
  { title: "检测对象", key: "target_label", minWidth: 200, ellipsis: { tooltip: true }, render: (r) => r.target_label || r.target_id.slice(0, 8) },
  { title: "结论", key: "conclusion", width: 100, render: (r) => h(NTag, { size: "small", type: RUN_TONE[r.conclusion], round: true }, () => RUN_CONCL_LABEL[r.conclusion]) },
  { title: "总分", key: "overall_score", width: 70, render: (r) => h("span", { class: "tabular-nums" }, String(r.overall_score)) },
  { title: "通过/警告/不过/待办", key: "stat", width: 150, render: (r) => `${r.passed} / ${r.warned} / ${r.failed} / ${r.manual_pending}` },
  { title: "操作", key: "actions", width: 110, fixed: "right", render: (r) => h(NButton, { size: "small", type: "primary", tertiary: true, onClick: () => emit("openRun", r.id) }, () => "单件报告") },
];

async function reload() {
  if (!props.batchId) { batch.value = null; return; }
  batch.value = (await PreservationAPI.getBatch(props.batchId)).data;
}

function printBatch() {
  const b = batch.value;
  if (!b) return;
  const w = window.open("", "_blank");
  if (!w) return;
  const esc = (v: string) => v.replace(/&/g, "&amp;").replace(/</g, "&lt;").replace(/>/g, "&gt;");
  const dims = ["authenticity", "integrity", "usability", "safety"].map((x) => `${DIM_LABEL[x]} ${(b.dim_scores ?? {})[x] ?? 0}`).join(" · ");
  const rows = b.runs.map((r, i) => `<tr><td>${i + 1}</td><td>${esc(r.target_label || "")}</td><td>${RUN_CONCL_LABEL[r.conclusion]}</td><td>${r.overall_score}</td></tr>`).join("");
  w.document.write(`<!doctype html><html><head><meta charset="utf-8"><title>四性检测批次报告</title>
    <style>body{font-family:"Microsoft YaHei",sans-serif;padding:32px;color:#111}
    h1{text-align:center;font-size:20px;margin-bottom:4px}.meta{text-align:center;color:#555;font-size:13px;margin-bottom:14px}
    .concl{font-size:15px;margin:10px 0;font-weight:bold}
    table{width:100%;border-collapse:collapse;font-size:12px}th,td{border:1px solid #999;padding:5px 8px;text-align:left}th{background:#f0f0f0}</style></head><body>
    <h1>电子档案四性检测批次报告</h1>
    <div class="meta">批次号 ${esc(b.batch_no)} ｜ 范围 ${esc(b.scope_label || "")} ｜ 方案 ${esc(b.scheme_name || "")} ｜ ${fmt(b.finished_at)}</div>
    <div class="concl">批次结论：${CONCLUSION_LABEL[b.conclusion]}（共 ${b.total} 件：合格 ${b.passed} · 基本合格 ${b.warned} · 不合格 ${b.failed} · 待复核 ${b.pending} ｜ 平均分 ${b.avg_score}）</div>
    <div class="concl" style="font-weight:normal">维度均分：${dims}</div>
    <table><thead><tr><th>序号</th><th>检测对象</th><th>结论</th><th>总分</th></tr></thead><tbody>${rows}</tbody></table>
    </body></html>`);
  w.document.close(); w.focus();
  setTimeout(() => w.print(), 300);
}

watch(() => props.batchId, reload);
onMounted(reload);
defineExpose({ reload });
</script>
