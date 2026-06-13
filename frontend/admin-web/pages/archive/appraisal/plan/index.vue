<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="鉴定计划"
      description="圈定到期档案，按全宗分配开放鉴定任务，指定鉴定员与审核员"
      icon="heroicons:calendar"
    />

    <!-- 工具栏 -->
    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <NSelect
        v-model:value="filterStatus"
        :options="statusOptions"
        placeholder="全部状态"
        clearable
        style="width: 160px"
        @update:value="loadPlans"
      />
      <NButton tertiary @click="loadPlans">
        <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
        刷新
      </NButton>
      <div class="flex-1" />
      <NButton type="primary" @click="openCreate">
        <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
        制定鉴定计划
      </NButton>
    </div>

    <!-- 计划列表 -->
    <div class="pro-card p-5">
      <ProTable :columns="columns" :data="plans" :loading="loading" :page-size="10" size="small" />
    </div>

    <!-- 创建计划向导 -->
    <NModal
      v-model:show="showCreate"
      preset="card"
      title="制定开放鉴定计划"
      style="width: 860px; max-width: 95vw"
      :mask-closable="false"
    >
      <div class="flex flex-col gap-4">
        <div class="grid grid-cols-2 gap-4">
          <div class="flex flex-col gap-1">
            <span class="text-sm font-medium">计划名称 <span class="text-red-500">*</span></span>
            <NInput v-model:value="form.name" placeholder="如：2026年度档案开放鉴定" />
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-sm font-medium">审核员 <span class="text-red-500">*</span></span>
            <NSelect v-model:value="form.reviewer_id" :options="userOptions" filterable placeholder="审核鉴定结论的人" />
          </div>
        </div>
        <div class="flex flex-col gap-1">
          <span class="text-sm font-medium">说明</span>
          <NInput v-model:value="form.description" type="textarea" :rows="2" placeholder="可选" />
        </div>

        <!-- 圈定预览 + 任务分配 -->
        <div class="flex items-center justify-between">
          <p class="text-sm font-medium">
            到期待鉴定档案
            <span class="text-gray-400 font-normal ml-1">
              共 {{ preview?.total ?? 0 }} 件 · 勾选全宗并指定鉴定员
            </span>
          </p>
          <NButton size="small" tertiary :loading="previewLoading" @click="loadPreview">
            <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
            重新圈定
          </NButton>
        </div>

        <div class="border rounded-lg overflow-hidden">
          <div class="grid grid-cols-[40px_1fr_1fr_120px_1.2fr] gap-px bg-gray-100 text-xs font-medium text-gray-500">
            <div class="bg-gray-50 px-2 py-1.5" />
            <div class="bg-gray-50 px-2 py-1.5">全宗号</div>
            <div class="bg-gray-50 px-2 py-1.5">全宗名称</div>
            <div class="bg-gray-50 px-2 py-1.5">到期档案</div>
            <div class="bg-gray-50 px-2 py-1.5">鉴定员</div>
          </div>
          <div class="max-h-64 overflow-y-auto">
            <div
              v-for="g in preview?.groups ?? []"
              :key="g.fonds_id"
              class="grid grid-cols-[40px_1fr_1fr_120px_1.2fr] gap-px bg-gray-100 items-center"
            >
              <div class="bg-white flex justify-center py-1.5">
                <NCheckbox :checked="!!assigns[g.fonds_id]" @update:checked="(v: boolean) => toggleFonds(g.fonds_id, v)" />
              </div>
              <div class="bg-white px-2 py-1.5 text-sm">{{ g.QZH }}</div>
              <div class="bg-white px-2 py-1.5 text-sm">{{ g.fonds_name }}</div>
              <div class="bg-white px-2 py-1.5 text-sm">{{ g.due_count }} 件</div>
              <div class="bg-white px-1 py-1">
                <NSelect
                  :value="assigns[g.fonds_id] ?? null"
                  :options="userOptions"
                  :disabled="!(g.fonds_id in assigns)"
                  size="small"
                  filterable
                  placeholder="选择鉴定员"
                  @update:value="(v: string) => { assigns[g.fonds_id] = v; }"
                />
              </div>
            </div>
          </div>
          <div v-if="!previewLoading && !(preview?.groups?.length)" class="py-8 text-center text-sm text-gray-400 bg-white">
            当前没有到期待鉴定的档案
          </div>
        </div>
      </div>

      <template #footer>
        <div class="flex justify-end gap-3">
          <NButton @click="showCreate = false">取消</NButton>
          <NButton type="primary" :loading="saving" @click="submitCreate">创建计划</NButton>
        </div>
      </template>
    </NModal>

    <!-- 计划详情 -->
    <NModal
      v-model:show="showDetail"
      preset="card"
      :title="`鉴定计划 ${detail?.plan_no ?? ''}`"
      style="width: 860px; max-width: 95vw"
    >
      <div v-if="detail" class="flex flex-col gap-4">
        <div class="flex items-center gap-3 text-sm text-gray-500">
          <NTag :type="detail.status === 'completed' ? 'success' : 'info'" size="small" round>
            {{ detail.status === "completed" ? "已完成" : "进行中" }}
          </NTag>
          <span>{{ detail.name }}</span>
          <span>· 组长 {{ detail.leader_name }}</span>
          <span>· 审核员 {{ detail.reviewer_name }}</span>
          <span>· {{ detail.total_archives }} 件 / {{ detail.total_tasks }} 个任务</span>
        </div>
        <ProTable :columns="taskColumns" :data="detail.tasks ?? []" :page-size="0" size="small" max-height="320" />
      </div>
    </NModal>
  </div>
</template>

<script setup lang="tsx">
import { h, onMounted, reactive, ref } from "vue";
import { NButton, NCheckbox, NInput, NModal, NSelect, NTag, useMessage } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { AppraisalTaskStatusTag } from "@/components/archive";
import { AppraisalAPI } from "@/api/appraisal";
import type { AppraisalPlan, AppraisalTask, PlanStatus, ScopePreview } from "@/api/appraisal";
import { UserAPI } from "@/api/iam";
import type { User } from "@/api/iam";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();

const statusOptions = [
  { label: "进行中", value: "in_progress" },
  { label: "已完成", value: "completed" },
];

// ── 列表 ──────────────────────────────────────────────────────────────────────
const loading = ref(false);
const plans = ref<AppraisalPlan[]>([]);
const filterStatus = ref<PlanStatus | null>(null);

async function loadPlans() {
  loading.value = true;
  try {
    const res = await AppraisalAPI.listPlans({ status: filterStatus.value ?? undefined, limit: 100 });
    plans.value = res.data.items;
  } finally {
    loading.value = false;
  }
}

const columns: DataTableColumns<AppraisalPlan> = [
  { title: "计划编号", key: "plan_no", width: 150 },
  { title: "计划名称", key: "name", ellipsis: { tooltip: true } },
  { title: "组长", key: "leader_name", width: 110 },
  { title: "审核员", key: "reviewer_name", width: 110 },
  { title: "任务", key: "total_tasks", width: 70, render: (r) => `${r.total_tasks} 个` },
  { title: "档案", key: "total_archives", width: 80, render: (r) => `${r.total_archives} 件` },
  {
    title: "状态", key: "status", width: 100,
    render: (r) => h(NTag, { type: r.status === "completed" ? "success" : "info", size: "small", round: true },
      { default: () => (r.status === "completed" ? "已完成" : "进行中") }),
  },
  { title: "创建时间", key: "create_time", width: 110, render: (r) => r.create_time?.slice(0, 10) },
  {
    title: "操作", key: "actions", width: 90,
    render: (r) => h(NButton, { size: "small", tertiary: true, onClick: () => openDetail(r.id) }, { default: () => "详情" }),
  },
];

// ── 详情 ──────────────────────────────────────────────────────────────────────
const showDetail = ref(false);
const detail = ref<AppraisalPlan | null>(null);

async function openDetail(id: string) {
  const res = await AppraisalAPI.getPlan(id);
  detail.value = res.data;
  showDetail.value = true;
}

const taskColumns: DataTableColumns<AppraisalTask> = [
  { title: "全宗", key: "QZH", width: 100, render: (r) => `${r.QZH}` },
  { title: "全宗名称", key: "fonds_name", ellipsis: { tooltip: true } },
  { title: "鉴定员", key: "assignee_name", width: 110 },
  { title: "进度", key: "decided", width: 100, render: (r) => `${r.decided}/${r.total}` },
  { title: "状态", key: "status", width: 130, render: (r) => h(AppraisalTaskStatusTag, { status: r.status }) },
];

// ── 创建 ──────────────────────────────────────────────────────────────────────
const showCreate = ref(false);
const saving = ref(false);
const previewLoading = ref(false);
const preview = ref<ScopePreview | null>(null);
const assigns = ref<Record<string, string | null>>({});
const form = reactive({ name: "", reviewer_id: null as string | null, description: "" });

const userOptions = ref<{ label: string; value: string }[]>([]);

async function loadUsers() {
  const res = await UserAPI.list();
  userOptions.value = (res.data ?? []).map((u: User) => ({
    label: u.full_name ? `${u.full_name}（${u.username}）` : u.username,
    value: u.id,
  }));
}

async function loadPreview() {
  previewLoading.value = true;
  try {
    const res = await AppraisalAPI.scopePreview();
    preview.value = res.data;
  } finally {
    previewLoading.value = false;
  }
}

function toggleFonds(fondsId: string, checked: boolean) {
  if (checked) {
    assigns.value = { ...assigns.value, [fondsId]: null };
  } else {
    assigns.value = Object.fromEntries(
      Object.entries(assigns.value).filter(([k]) => k !== fondsId),
    );
  }
}

function openCreate() {
  form.name = `${new Date().getFullYear()}年度档案开放鉴定`;
  form.reviewer_id = null;
  form.description = "";
  assigns.value = {};
  showCreate.value = true;
  loadPreview();
}

async function submitCreate() {
  if (!form.name.trim()) return message.warning("请填写计划名称");
  if (!form.reviewer_id) return message.warning("请选择审核员");
  const tasks = Object.entries(assigns.value).map(([fonds_id, assignee_id]) => ({ fonds_id, assignee_id }));
  if (!tasks.length) return message.warning("请至少勾选一个全宗");
  if (tasks.some((t) => !t.assignee_id)) return message.warning("勾选的全宗都要指定鉴定员");

  saving.value = true;
  try {
    const res = await AppraisalAPI.createPlan({
      name: form.name.trim(),
      reviewer_id: form.reviewer_id,
      description: form.description || undefined,
      tasks: tasks as { fonds_id: string; assignee_id: string }[],
    });
    if (res.code === 0) {
      message.success(`计划 ${res.data.plan_no} 创建成功，已分配 ${res.data.total_tasks} 个任务`);
      showCreate.value = false;
      loadPlans();
    } else {
      message.error(res.message);
    }
  } finally {
    saving.value = false;
  }
}

onMounted(() => {
  loadPlans();
  loadUsers();
});
</script>
