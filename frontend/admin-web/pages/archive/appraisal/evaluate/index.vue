<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="鉴定工作"
      description="我的开放鉴定任务：AI 预鉴定 → 人工核对结论 → 提交审核"
      icon="heroicons:clipboard-document-list"
    />

    <!-- 任务列表 -->
    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <NSelect
        v-model:value="filterStatus"
        :options="statusOptions"
        placeholder="全部状态"
        clearable
        style="width: 160px"
        @update:value="loadTasks"
      />
      <NButton tertiary @click="loadTasks">
        <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
        刷新
      </NButton>
    </div>

    <div class="pro-card p-5">
      <ProTable :columns="taskColumns" :data="tasks" :loading="loading" :page-size="10" size="small" />
    </div>

    <!-- 任务工作台 -->
    <NModal
      v-model:show="showWork"
      preset="card"
      :title="`鉴定任务 · 全宗 ${task?.QZH ?? ''} ${task?.fonds_name ?? ''}`"
      style="width: 1200px; max-width: 96vw"
      :mask-closable="false"
    >
      <div v-if="task" class="flex flex-col gap-4">
        <!-- 状态条 -->
        <div class="flex items-center flex-wrap gap-3">
          <AppraisalTaskStatusTag :status="task.status" />
          <span class="text-sm text-gray-500">{{ task.plan_name }}（{{ task.plan_no }}）</span>
          <span class="text-sm text-gray-500">共 {{ task.total }} 件 · 已定 {{ task.decided }} 件</span>
          <div class="flex-1" />
          <NButton
            v-if="editable"
            size="small"
            type="primary"
            secondary
            :loading="aiRunning"
            @click="runAi"
          >
            <template #icon><Icon name="heroicons:sparkles" class="w-4 h-4" /></template>
            AI 预鉴定
          </NButton>
          <NButton v-if="editable" size="small" :disabled="!hasAdoptable" @click="adoptAi">
            <template #icon><Icon name="heroicons:check" class="w-4 h-4" /></template>
            批量采纳 AI 建议
          </NButton>
          <NButton
            v-if="editable"
            size="small"
            type="primary"
            :disabled="task.decided < task.total"
            :loading="submitting"
            @click="submitTask"
          >
            <template #icon><Icon name="heroicons:paper-airplane" class="w-4 h-4" /></template>
            提交审核
          </NButton>
        </div>

        <div v-if="task.reject_reason" class="rounded-lg border border-red-200 bg-red-50 p-3 text-sm text-red-600">
          审核驳回：{{ task.reject_reason }}
        </div>

        <!-- 明细筛选 -->
        <div class="flex items-center gap-3">
          <NSelect
            v-model:value="itemStatus"
            :options="[{ label: '未定结论', value: 'pending' }, { label: '已定结论', value: 'decided' }]"
            placeholder="全部明细"
            clearable
            size="small"
            style="width: 140px"
            @update:value="loadItems"
          />
          <NInput
            v-model:value="itemKeyword"
            placeholder="题名 / 档号"
            size="small"
            clearable
            style="width: 200px"
            @keyup.enter="loadItems"
            @clear="loadItems"
          />
        </div>

        <ProTable
          :columns="itemColumns"
          :data="items"
          :loading="itemsLoading"
          :page-size="0"
          size="small"
          max-height="440"
        />
        <div class="flex justify-end">
          <NPagination
            v-model:page="itemPage"
            :page-size="ITEM_PAGE_SIZE"
            :item-count="itemTotal"
            size="small"
            @update:page="loadItems"
          />
        </div>
      </div>
    </NModal>

    <!-- 单条改判 -->
    <NModal
      v-model:show="showDecide"
      preset="card"
      title="人工鉴定结论"
      style="width: 560px; max-width: 95vw"
    >
      <div v-if="decideItem" class="flex flex-col gap-4">
        <div class="text-sm">
          <p class="font-medium">{{ decideItem.TM }}</p>
          <p class="text-gray-500 mt-1">{{ decideItem.DH }} · {{ decideItem.due_basis }}</p>
        </div>
        <div v-if="decideItem.ai_kfzt" class="rounded-lg border border-blue-200 bg-blue-50 p-3 text-sm">
          <p class="flex items-center gap-1.5 font-medium text-blue-600">
            <Icon name="heroicons:sparkles" class="w-4 h-4" />
            AI 建议：{{ decideItem.ai_kfzt }}
          </p>
          <p class="text-gray-600 mt-1">{{ decideItem.ai_reason }}</p>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">开放状态 <span class="text-red-500">*</span></span>
          <NSelect v-model:value="decideForm.final_kfzt" :options="kfztOptions" placeholder="选择结论" />
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">结论理由</span>
          <NInput v-model:value="decideForm.final_reason" type="textarea" :rows="3" placeholder="开放/划控的理由" />
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">引用标准条款</span>
          <NSelect
            v-model:value="decideForm.final_standard_code"
            :options="standardOptions"
            clearable
            filterable
            placeholder="可选"
            @update:value="onStandardPick"
          />
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <NButton @click="showDecide = false">取消</NButton>
          <NButton type="primary" :loading="deciding" @click="submitDecide">保存结论</NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="tsx">
import { computed, h, onBeforeUnmount, onMounted, reactive, ref, resolveComponent } from "vue";
import { NButton, NInput, NModal, NPagination, NSelect, NTooltip, useMessage } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { AppraisalTaskStatusTag, KfztTag } from "@/components/archive";
import { AppraisalAPI, AppraisalStandardAPI } from "@/api/appraisal";
import type { AppraisalItem, AppraisalTask, Kfzt, TaskStatus } from "@/api/appraisal";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const IconComp = resolveComponent("Icon");
const ITEM_PAGE_SIZE = 50;

const statusOptions = [
  { label: "待鉴定", value: "pending" },
  { label: "AI 预鉴定中", value: "ai_running" },
  { label: "AI 预鉴完成", value: "ai_done" },
  { label: "待审核", value: "submitted" },
  { label: "已通过", value: "approved" },
  { label: "已驳回", value: "rejected" },
];
const kfztOptions = (["开放", "控制使用", "延期开放", "不开放"] as Kfzt[]).map((v) => ({ label: v, value: v }));

// ── 任务列表 ──────────────────────────────────────────────────────────────────
const loading = ref(false);
const tasks = ref<AppraisalTask[]>([]);
const filterStatus = ref<TaskStatus | null>(null);

async function loadTasks() {
  loading.value = true;
  try {
    const res = await AppraisalAPI.listTasks({ role: "assignee", status: filterStatus.value ?? undefined, limit: 100 });
    tasks.value = res.data.items;
  } finally {
    loading.value = false;
  }
}

const taskColumns: DataTableColumns<AppraisalTask> = [
  { title: "计划", key: "plan_name", ellipsis: { tooltip: true }, render: (r) => `${r.plan_name}（${r.plan_no}）` },
  { title: "全宗", key: "QZH", width: 90 },
  { title: "全宗名称", key: "fonds_name", ellipsis: { tooltip: true } },
  { title: "进度", key: "decided", width: 90, render: (r) => `${r.decided}/${r.total}` },
  { title: "状态", key: "status", width: 130, render: (r) => h(AppraisalTaskStatusTag, { status: r.status }) },
  { title: "分配时间", key: "create_time", width: 110, render: (r) => r.create_time?.slice(0, 10) },
  {
    title: "操作", key: "actions", width: 110,
    render: (r) => h(NButton, { size: "small", type: "primary", tertiary: true, onClick: () => openWork(r.id) },
      { default: () => (["approved", "submitted"].includes(r.status) ? "查看" : "去鉴定") }),
  },
];

// ── 任务工作台 ────────────────────────────────────────────────────────────────
const showWork = ref(false);
const task = ref<AppraisalTask | null>(null);
const items = ref<AppraisalItem[]>([]);
const itemsLoading = ref(false);
const itemStatus = ref<"pending" | "decided" | null>(null);
const itemKeyword = ref("");
const itemPage = ref(1);
const itemTotal = ref(0);
const aiRunning = ref(false);
const submitting = ref(false);
let pollTimer: ReturnType<typeof setInterval> | null = null;

const editable = computed(() => !!task.value && ["pending", "ai_running", "ai_done", "rejected"].includes(task.value.status));
const hasAdoptable = computed(() => items.value.some((i) => i.status === "pending" && i.ai_kfzt));

async function openWork(id: string) {
  const res = await AppraisalAPI.getTask(id);
  task.value = res.data;
  itemStatus.value = null;
  itemKeyword.value = "";
  itemPage.value = 1;
  showWork.value = true;
  await loadItems();
  if (task.value?.status === "ai_running") startPoll();
}

async function refreshTask() {
  if (!task.value) return;
  const res = await AppraisalAPI.getTask(task.value.id);
  task.value = res.data;
}

async function loadItems() {
  if (!task.value) return;
  itemsLoading.value = true;
  try {
    const res = await AppraisalAPI.listItems(task.value.id, {
      status: itemStatus.value ?? undefined,
      keyword: itemKeyword.value || undefined,
      skip: (itemPage.value - 1) * ITEM_PAGE_SIZE,
      limit: ITEM_PAGE_SIZE,
    });
    items.value = res.data.items;
    itemTotal.value = res.data.total;
  } finally {
    itemsLoading.value = false;
  }
}

async function runAi() {
  if (!task.value) return;
  aiRunning.value = true;
  try {
    const res = await AppraisalAPI.runAi(task.value.id);
    if (res.code === 0) {
      message.success("规则预鉴定完成，AI 语义复核后台进行中");
      await refreshTask();
      await loadItems();
      startPoll();
    } else {
      message.error(res.message);
    }
  } finally {
    aiRunning.value = false;
  }
}

function startPoll() {
  stopPoll();
  pollTimer = setInterval(async () => {
    await refreshTask();
    if (task.value?.status !== "ai_running") {
      stopPoll();
      await loadItems();
      message.success("AI 预鉴定全部完成");
    }
  }, 3000);
}

function stopPoll() {
  if (pollTimer) {
    clearInterval(pollTimer);
    pollTimer = null;
  }
}

async function adoptAi() {
  if (!task.value) return;
  const res = await AppraisalAPI.adoptAi(task.value.id);
  if (res.code === 0) {
    message.success(`已采纳 ${res.data.adopted} 条 AI 建议`);
    await refreshTask();
    await loadItems();
  } else {
    message.error(res.message);
  }
}

async function submitTask() {
  if (!task.value) return;
  submitting.value = true;
  try {
    const res = await AppraisalAPI.submitTask(task.value.id);
    if (res.code === 0) {
      message.success("已提交审核");
      showWork.value = false;
      loadTasks();
    } else {
      message.error(res.message);
    }
  } finally {
    submitting.value = false;
  }
}

// ── 明细表格 ──────────────────────────────────────────────────────────────────
const itemColumns = computed<DataTableColumns<AppraisalItem>>(() => [
  { title: "档号", key: "DH", width: 190, ellipsis: { tooltip: true } },
  { title: "题名", key: "TM", minWidth: 200, ellipsis: { tooltip: true } },
  { title: "年度", key: "ND", width: 60 },
  { title: "密级", key: "MJ", width: 70 },
  { title: "到期依据", key: "due_basis", width: 180, ellipsis: { tooltip: true } },
  {
    title: "AI 建议", key: "ai_kfzt", width: 120,
    render: (r) => {
      if (!r.ai_kfzt) return h("span", { class: "text-xs text-gray-400" }, "未预鉴定");
      return h(NTooltip, null, {
        trigger: () => h("div", { class: "inline-flex items-center gap-1" }, [
          h(KfztTag, { value: r.ai_kfzt }),
          r.ai_hit_words?.length
            ? h(IconComp, { name: "heroicons:exclamation-triangle", class: "w-3.5 h-3.5 text-amber-500" })
            : null,
        ]),
        default: () => r.ai_reason ?? "",
      });
    },
  },
  {
    title: "人工结论", key: "final_kfzt", width: 100,
    render: (r) => (r.status === "decided"
      ? h(KfztTag, { value: r.final_kfzt })
      : h("span", { class: "text-xs text-gray-400" }, "未定")),
  },
  {
    title: "操作", key: "actions", width: 90,
    render: (r) => (editable.value
      ? h(NButton, { size: "tiny", tertiary: true, onClick: () => openDecide(r) }, { default: () => (r.status === "decided" ? "改判" : "下结论") })
      : null),
  },
]);

// ── 单条结论 ──────────────────────────────────────────────────────────────────
const showDecide = ref(false);
const deciding = ref(false);
const decideItem = ref<AppraisalItem | null>(null);
const decideForm = reactive({
  final_kfzt: null as Kfzt | null,
  final_reason: "",
  final_standard_code: null as string | null,
});
const standardOptions = ref<{ label: string; value: string; kfzt: Kfzt; content: string }[]>([]);

async function loadStandards() {
  const res = await AppraisalStandardAPI.list(true);
  standardOptions.value = (res.data ?? []).map((s) => ({
    label: `${s.code} ${s.title}`,
    value: s.code,
    kfzt: s.target_kfzt,
    content: s.content,
  }));
}

function onStandardPick(code: string | null) {
  const std = standardOptions.value.find((s) => s.value === code);
  if (std) {
    decideForm.final_kfzt = std.kfzt;
    if (!decideForm.final_reason) decideForm.final_reason = std.content;
  }
}

function openDecide(item: AppraisalItem) {
  decideItem.value = item;
  decideForm.final_kfzt = item.final_kfzt ?? item.ai_kfzt ?? null;
  decideForm.final_reason = item.final_reason ?? item.ai_reason ?? "";
  decideForm.final_standard_code = item.final_standard_code ?? item.ai_standard_code ?? null;
  showDecide.value = true;
}

async function submitDecide() {
  if (!decideItem.value) return;
  if (!decideForm.final_kfzt) return message.warning("请选择开放状态结论");
  deciding.value = true;
  try {
    const res = await AppraisalAPI.decideItem(decideItem.value.id, {
      final_kfzt: decideForm.final_kfzt,
      final_reason: decideForm.final_reason || undefined,
      final_standard_code: decideForm.final_standard_code ?? undefined,
    });
    if (res.code === 0) {
      message.success("结论已保存");
      showDecide.value = false;
      await refreshTask();
      await loadItems();
    } else {
      message.error(res.message);
    }
  } finally {
    deciding.value = false;
  }
}

onMounted(() => {
  loadTasks();
  loadStandards();
});
onBeforeUnmount(stopPoll);
</script>
