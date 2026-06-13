<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="年度报表"
      description="按《全国档案事业统计调查制度》（DA-2 表口径）编制：系统指标一键生成，人工指标补填后定稿"
      icon="heroicons:document-chart-bar"
    />

    <!-- 工具栏 -->
    <div class="pro-card p-4 flex flex-wrap items-center gap-3 print:hidden">
      <NSelect
        v-model:value="year"
        :options="yearOptions"
        style="width: 140px"
        @update:value="load"
      />
      <NTag v-if="report" :type="statusMeta.type" round size="small">{{ statusMeta.label }}</NTag>
      <span v-if="report?.generated_at" class="text-[12px]" style="color:var(--semi-color-text-3)">
        系统指标生成于 {{ report.generated_at.slice(0, 19).replace("T", " ") }}
      </span>
      <div class="flex-1" />
      <NButton v-if="editable" type="primary" secondary :loading="generating" @click="generate">
        <template #icon><Icon name="heroicons:bolt" class="w-4 h-4" /></template>
        {{ report?.status === "none" ? "一键生成" : "重算系统指标" }}
      </NButton>
      <NButton v-if="editable && report?.status === 'draft'" :loading="saving" @click="save">
        <template #icon><Icon name="heroicons:check" class="w-4 h-4" /></template>
        保存填报
      </NButton>
      <NButton v-if="report?.status === 'draft'" type="primary" :loading="acting" @click="finalize">
        <template #icon><Icon name="heroicons:lock-closed" class="w-4 h-4" /></template>
        定稿
      </NButton>
      <NButton v-if="report?.status === 'final'" :loading="acting" @click="reopen">
        <template #icon><Icon name="heroicons:lock-open" class="w-4 h-4" /></template>
        撤回定稿
      </NButton>
      <NButton v-if="report && report.status !== 'none'" tertiary @click="printReport">
        <template #icon><Icon name="heroicons:printer" class="w-4 h-4" /></template>
        打印
      </NButton>
    </div>

    <!-- 报表主体 -->
    <div v-if="report" class="flex flex-col gap-4" :class="{ 'opacity-60': report.status === 'none' }">
      <div class="hidden print:block text-center">
        <h2 class="text-[18px] font-bold">档案馆基本情况年报（{{ year }} 年度）</h2>
        <p class="text-[12px]">依据《全国档案事业统计调查制度》DA-2 表口径编制</p>
      </div>

      <div
        v-if="report.status === 'none'"
        class="pro-card p-6 text-center text-[13px] print:hidden"
        style="color:var(--semi-color-text-2)"
      >
        {{ year }} 年度报表尚未生成，点击右上角「一键生成」自动计算系统指标
      </div>

      <div v-for="group in report.definitions ?? []" :key="group.key" class="pro-card p-5">
        <p class="text-[14px] font-semibold mb-3" style="color:var(--semi-color-text-0)">{{ group.name }}</p>
        <div class="grid grid-cols-1 md:grid-cols-2 gap-x-8 gap-y-2">
          <div
            v-for="item in group.items"
            :key="item.key"
            class="flex items-center gap-3 py-1.5"
            style="border-bottom:1px dashed var(--semi-color-border)"
          >
            <div class="flex-1 min-w-0">
              <span class="text-[13px]" style="color:var(--semi-color-text-1)">{{ item.label }}</span>
              <NTooltip v-if="item.hint">
                <template #trigger>
                  <Icon name="heroicons:question-mark-circle" class="w-3.5 h-3.5 ml-1 inline-block align-text-top print:hidden" style="color:var(--semi-color-text-3)" />
                </template>
                {{ item.hint }}
              </NTooltip>
            </div>
            <NTag size="tiny" :bordered="false" :type="item.source === 'auto' ? 'info' : 'default'" class="print:hidden">
              {{ item.source === "auto" ? "系统" : "填报" }}
            </NTag>
            <div class="w-36 text-right">
              <span v-if="item.source === 'auto'" class="text-[14px] font-semibold tabular-nums" style="color:var(--semi-color-text-0)">
                {{ fmtValue(report.auto_data[item.key]) }}
              </span>
              <NInputNumber
                v-else-if="editable && report.status !== 'none'"
                v-model:value="manualForm[item.key]"
                size="small"
                :show-button="false"
                :min="0"
                placeholder="填报"
                class="w-full print:hidden"
              />
              <span v-else class="text-[14px] font-semibold tabular-nums" style="color:var(--semi-color-text-0)">
                {{ fmtValue(report.manual_data[item.key]) }}
              </span>
            </div>
            <span class="w-14 text-[11.5px]" style="color:var(--semi-color-text-3)">{{ item.unit }}</span>
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, reactive, ref } from "vue";
import { NButton, NInputNumber, NSelect, NTag, NTooltip, useDialog, useMessage } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { StatisticsAPI } from "@/api/statistics";
import type { AnnualReport } from "@/api/statistics";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();

const year = ref(new Date().getFullYear() - 1);
const yearOptions = (() => {
  const cur = new Date().getFullYear();
  return Array.from({ length: 6 }, (_, i) => ({ label: `${cur - i} 年度`, value: cur - i }));
})();

const report = ref<AnnualReport | null>(null);
const manualForm = reactive<Record<string, number | null>>({});
const generating = ref(false);
const saving = ref(false);
const acting = ref(false);

const editable = computed(() => report.value?.status !== "final");
const statusMeta = computed(() => {
  switch (report.value?.status) {
    case "final": return { label: "已定稿", type: "success" as const };
    case "draft": return { label: "编制中", type: "info" as const };
    default: return { label: "未生成", type: "default" as const };
  }
});

function fmtValue(v?: number): string {
  return v === undefined || v === null ? "—" : Number(v).toLocaleString();
}

function syncManualForm() {
  Object.keys(manualForm).forEach((k) => { manualForm[k] = null; });
  Object.entries(report.value?.manual_data ?? {}).forEach(([k, v]) => {
    manualForm[k] = v;
  });
}

async function load() {
  const res = await StatisticsAPI.getAnnualReport(year.value);
  if (res.code === 0) {
    report.value = res.data;
    syncManualForm();
  }
}

async function generate() {
  generating.value = true;
  try {
    const res = await StatisticsAPI.generateAnnualReport(year.value);
    if (res.code === 0) {
      report.value = res.data;
      syncManualForm();
      message.success("系统指标已生成，人工指标请补填后定稿");
    } else {
      message.error(res.message);
    }
  } finally {
    generating.value = false;
  }
}

function collectManual(): Record<string, number> {
  return Object.fromEntries(
    Object.entries(manualForm).filter(([, v]) => v !== null && v !== undefined),
  ) as Record<string, number>;
}

async function save() {
  saving.value = true;
  try {
    const res = await StatisticsAPI.saveAnnualReport(year.value, collectManual());
    if (res.code === 0) {
      report.value = { ...report.value!, manual_data: res.data.manual_data };
      message.success("填报已保存");
    } else {
      message.error(res.message);
    }
  } finally {
    saving.value = false;
  }
}

function finalize() {
  dialog.warning({
    title: "定稿确认",
    content: `定稿后 ${year.value} 年度报表将锁定，不能再重算或修改（可撤回）。确认定稿？`,
    positiveText: "确认定稿",
    negativeText: "再检查下",
    onPositiveClick: async () => {
      acting.value = true;
      try {
        await StatisticsAPI.saveAnnualReport(year.value, collectManual());
        const res = await StatisticsAPI.finalizeAnnualReport(year.value);
        if (res.code === 0) {
          message.success("年报已定稿");
          await load();
        } else {
          message.error(res.message);
        }
      } finally {
        acting.value = false;
      }
    },
  });
}

async function reopen() {
  acting.value = true;
  try {
    const res = await StatisticsAPI.reopenAnnualReport(year.value);
    if (res.code === 0) {
      message.success("已撤回定稿，可继续编辑");
      await load();
    } else {
      message.error(res.message);
    }
  } finally {
    acting.value = false;
  }
}

function printReport() {
  window.print();
}

onMounted(load);
</script>
