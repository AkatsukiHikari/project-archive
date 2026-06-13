<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="鉴定审核"
      description="审核鉴定员提交的开放鉴定结论，通过后结论回写档案"
      icon="heroicons:check-circle"
    />

    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <NSelect
        v-model:value="filterStatus"
        :options="statusOptions"
        placeholder="待审核"
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

    <!-- 审核详情 -->
    <NModal
      v-model:show="showDetail"
      preset="card"
      :title="`鉴定审核 · 全宗 ${task?.QZH ?? ''} ${task?.fonds_name ?? ''}`"
      style="width: 1160px; max-width: 96vw"
      :mask-closable="false"
    >
      <div v-if="task" class="flex flex-col gap-4">
        <div class="flex items-center flex-wrap gap-3">
          <AppraisalTaskStatusTag :status="task.status" />
          <span class="text-sm text-gray-500">{{ task.plan_name }}（{{ task.plan_no }}）</span>
          <span class="text-sm text-gray-500">鉴定员 {{ task.assignee_name }}</span>
          <span class="text-sm text-gray-500">共 {{ task.total }} 件</span>
          <div class="flex-1" />
          <!-- 结论分布 -->
          <div class="flex items-center gap-2">
            <span v-for="(n, k) in kfztStats" :key="k" class="inline-flex items-center gap-1 text-xs text-gray-500">
              <KfztTag :value="String(k)" />× {{ n }}
            </span>
          </div>
        </div>

        <NSelect
          v-model:value="itemKfzt"
          :options="kfztOptions"
          placeholder="按结论筛选"
          clearable
          size="small"
          style="width: 160px"
          @update:value="loadItems"
        />

        <ProTable
          :columns="itemColumns"
          :data="items"
          :loading="itemsLoading"
          :page-size="0"
          size="small"
          max-height="420"
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

      <template #footer>
        <div v-if="task?.status === 'submitted'" class="flex justify-end gap-3">
          <NButton type="error" tertiary :loading="acting" @click="openReject">
            <template #icon><Icon name="heroicons:arrow-uturn-left" class="w-4 h-4" /></template>
            驳回
          </NButton>
          <NButton type="primary" :loading="acting" @click="approve">
            <template #icon><Icon name="heroicons:check-badge" class="w-4 h-4" /></template>
            审核通过并回写档案
          </NButton>
        </div>
      </template>
    </NModal>

    <!-- 驳回原因 -->
    <NModal v-model:show="showReject" preset="card" title="驳回任务" style="width: 480px">
      <NInput v-model:value="rejectReason" type="textarea" :rows="3" placeholder="说明驳回原因，鉴定员将据此修改" />
      <template #footer>
        <div class="flex justify-end gap-3">
          <NButton @click="showReject = false">取消</NButton>
          <NButton type="error" :loading="acting" @click="reject">确认驳回</NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="tsx">
import { computed, h, onMounted, ref } from "vue";
import { NButton, NInput, NModal, NPagination, NSelect, NTooltip, useDialog, useMessage } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { AppraisalTaskStatusTag, KfztTag } from "@/components/archive";
import { AppraisalAPI } from "@/api/appraisal";
import type { AppraisalItem, AppraisalTask, Kfzt, TaskStatus } from "@/api/appraisal";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();
const ITEM_PAGE_SIZE = 50;

const statusOptions = [
  { label: "待审核", value: "submitted" },
  { label: "已通过", value: "approved" },
  { label: "已驳回", value: "rejected" },
];
const kfztOptions = (["开放", "控制使用", "延期开放", "不开放"] as Kfzt[]).map((v) => ({ label: v, value: v }));

// ── 任务列表 ──────────────────────────────────────────────────────────────────
const loading = ref(false);
const tasks = ref<AppraisalTask[]>([]);
const filterStatus = ref<TaskStatus | null>("submitted");

async function loadTasks() {
  loading.value = true;
  try {
    const res = await AppraisalAPI.listTasks({ role: "reviewer", status: filterStatus.value ?? undefined, limit: 100 });
    tasks.value = res.data.items;
  } finally {
    loading.value = false;
  }
}

const taskColumns: DataTableColumns<AppraisalTask> = [
  { title: "计划", key: "plan_name", ellipsis: { tooltip: true }, render: (r) => `${r.plan_name}（${r.plan_no}）` },
  { title: "全宗", key: "QZH", width: 90 },
  { title: "全宗名称", key: "fonds_name", ellipsis: { tooltip: true } },
  { title: "鉴定员", key: "assignee_name", width: 110 },
  { title: "件数", key: "total", width: 70 },
  { title: "状态", key: "status", width: 120, render: (r) => h(AppraisalTaskStatusTag, { status: r.status }) },
  { title: "提交时间", key: "submitted_at", width: 110, render: (r) => r.submitted_at?.slice(0, 10) ?? "—" },
  {
    title: "操作", key: "actions", width: 90,
    render: (r) => h(NButton, { size: "small", type: "primary", tertiary: true, onClick: () => openDetail(r.id) },
      { default: () => (r.status === "submitted" ? "去审核" : "查看") }),
  },
];

// ── 审核详情 ──────────────────────────────────────────────────────────────────
const showDetail = ref(false);
const task = ref<AppraisalTask | null>(null);
const items = ref<AppraisalItem[]>([]);
const itemsLoading = ref(false);
const itemKfzt = ref<Kfzt | null>(null);
const itemPage = ref(1);
const itemTotal = ref(0);
const allItems = ref<AppraisalItem[]>([]);
const acting = ref(false);

const kfztStats = computed(() => {
  const stats: Record<string, number> = {};
  for (const i of allItems.value) {
    if (i.final_kfzt) stats[i.final_kfzt] = (stats[i.final_kfzt] ?? 0) + 1;
  }
  return stats;
});

async function openDetail(id: string) {
  const res = await AppraisalAPI.getTask(id);
  task.value = res.data;
  itemKfzt.value = null;
  itemPage.value = 1;
  showDetail.value = true;
  const all = await AppraisalAPI.listItems(id, { limit: 200 });
  allItems.value = all.data.items;
  await loadItems();
}

async function loadItems() {
  if (!task.value) return;
  itemsLoading.value = true;
  try {
    const res = await AppraisalAPI.listItems(task.value.id, {
      skip: (itemPage.value - 1) * ITEM_PAGE_SIZE,
      limit: ITEM_PAGE_SIZE,
    });
    let list = res.data.items;
    if (itemKfzt.value) list = list.filter((i) => i.final_kfzt === itemKfzt.value);
    items.value = list;
    itemTotal.value = res.data.total;
  } finally {
    itemsLoading.value = false;
  }
}

const itemColumns: DataTableColumns<AppraisalItem> = [
  { title: "档号", key: "DH", width: 190, ellipsis: { tooltip: true } },
  { title: "题名", key: "TM", minWidth: 200, ellipsis: { tooltip: true } },
  { title: "年度", key: "ND", width: 60 },
  { title: "密级", key: "MJ", width: 70 },
  { title: "AI 建议", key: "ai_kfzt", width: 100, render: (r) => h(KfztTag, { value: r.ai_kfzt }) },
  {
    title: "人工结论", key: "final_kfzt", width: 100,
    render: (r) => h(KfztTag, { value: r.final_kfzt }),
  },
  {
    title: "结论理由", key: "final_reason", minWidth: 220,
    render: (r) => h(NTooltip, null, {
      trigger: () => h("span", { class: "text-xs text-gray-600 line-clamp-1" }, r.final_reason ?? "—"),
      default: () => r.final_reason ?? "—",
    }),
  },
];

function approve() {
  if (!task.value) return;
  dialog.warning({
    title: "审核通过",
    content: `确认通过该任务的 ${task.value.total} 条鉴定结论？开放状态将回写到档案，此操作进入鉴定台账。`,
    positiveText: "确认通过",
    negativeText: "再看看",
    onPositiveClick: async () => {
      acting.value = true;
      try {
        const res = await AppraisalAPI.approveTask(task.value!.id);
        if (res.code === 0) {
          message.success("审核通过，结论已回写档案");
          showDetail.value = false;
          loadTasks();
        } else {
          message.error(res.message);
        }
      } finally {
        acting.value = false;
      }
    },
  });
}

// ── 驳回 ──────────────────────────────────────────────────────────────────────
const showReject = ref(false);
const rejectReason = ref("");

function openReject() {
  rejectReason.value = "";
  showReject.value = true;
}

async function reject() {
  if (!task.value) return;
  if (!rejectReason.value.trim()) return message.warning("请填写驳回原因");
  acting.value = true;
  try {
    const res = await AppraisalAPI.rejectTask(task.value.id, rejectReason.value.trim());
    if (res.code === 0) {
      message.success("已驳回，任务退回鉴定员");
      showReject.value = false;
      showDetail.value = false;
      loadTasks();
    } else {
      message.error(res.message);
    }
  } finally {
    acting.value = false;
  }
}

onMounted(loadTasks);
</script>
