<template>
  <div class="flex flex-col gap-3 min-h-0 flex-1">
    <AdminPageHeader
      title="自助机申请"
      description="市民在自助查询机提交的查看申请：审批、驳回与办理跟踪"
      icon="heroicons:computer-desktop"
    />

    <!-- ── 筛选 ─────────────────────────────────────────── -->
    <div class="pro-card p-4 flex items-center gap-3 flex-wrap">
      <div class="flex items-center gap-1.5">
        <button
          v-for="t in statusTabs"
          :key="t.value"
          class="px-3.5 py-1.5 rounded-lg text-[13px] font-medium border-none cursor-pointer transition-colors"
          :style="statusFilter === t.value
            ? 'background:oklch(var(--p)/0.12);color:oklch(var(--p))'
            : 'background:var(--semi-color-fill-0);color:var(--semi-color-text-2)'"
          @click="switchStatus(t.value)"
        >
          {{ t.label }}
          <span v-if="t.value === 'pending' && pendingCount" class="ml-1 tabular-nums">({{ pendingCount }})</span>
        </button>
      </div>
      <div class="flex-1" />
      <NInput
        v-model:value="keyword"
        placeholder="姓名 / 登记号 / 申请码"
        clearable
        style="width: 240px"
        @keydown.enter="load"
        @clear="load"
      >
        <template #prefix><Icon name="heroicons:magnifying-glass" class="w-4 h-4" style="color: var(--semi-color-text-3)" /></template>
      </NInput>
      <NButton type="primary" :loading="loading" @click="load">检索</NButton>
      <NButton text size="small" :loading="loading" @click="load">
        <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
        刷新
      </NButton>
    </div>

    <!-- ── 列表 ─────────────────────────────────────────── -->
    <div class="pro-card p-4 flex-1 min-w-0 min-h-0 flex flex-col gap-3">
      <NDataTable
        :columns="columns"
        :data="rows"
        :loading="loading"
        :row-key="(r: UtilApplication) => r.id"
        size="small"
        class="flex-1"
        :scroll-x="1150"
      />
    </div>

    <!-- 详情抽屉 -->
    <NDrawer v-model:show="detailShow" :width="480" placement="right">
      <NDrawerContent title="申请详情" closable>
        <ApplicationDetailPanel :app-id="detailId" @changed="load" @completed="load" />
      </NDrawerContent>
    </NDrawer>

    <!-- 拒绝原因 -->
    <NModal
      v-model:show="rejectShow"
      preset="dialog"
      title="拒绝申请"
      positive-text="确认拒绝"
      negative-text="取消"
      @positive-click="doReject"
    >
      <div class="flex flex-col gap-2 py-2">
        <p class="text-[13px] m-0" style="color: var(--semi-color-text-2)">
          拒绝「{{ rejectTarget?.applicant_name }}」的查看申请，原因将显示在自助机上：
        </p>
        <NInput v-model:value="rejectReason" type="textarea" :rows="2" placeholder="如：所申请档案涉及个人隐私，请携带有效证件到柜台办理" />
      </div>
    </NModal>

    <TransferHandlerModal v-model:show="transferShow" :app-id="transferId" @done="load" />
  </div>
</template>

<script setup lang="tsx">
import { h, onActivated, onMounted, ref } from "vue";
import {
  NButton, NDataTable, NDrawer, NDrawerContent, NInput, NModal, NTag, useMessage,
} from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ApplicationDetailPanel, TransferHandlerModal } from "@/components/archive";
import { UtilizationAPI, type UtilApplication } from "@/api/utilization";

definePageMeta({
  layout: "service",
  middleware: "auth",
  breadcrumb: [
    { name: "利用服务中心", path: "/service" },
    { name: "自助机申请", path: "/service/kiosk-apps" },
  ],
});
useHead({ title: "自助机申请" });

const router = useRouter();
const message = useMessage();

// ── 筛选 / 加载 ───────────────────────────────────────────────────────────────
const statusTabs = [
  { label: "待审批", value: "pending" },
  { label: "办理中", value: "processing" },
  { label: "已拒绝", value: "rejected" },
  { label: "已办结", value: "completed" },
  { label: "全部", value: "" },
];
const statusFilter = ref("pending");
const keyword = ref("");
const rows = ref<UtilApplication[]>([]);
const loading = ref(false);
const pendingCount = ref(0);

async function load() {
  loading.value = true;
  try {
    const res = await UtilizationAPI.list({
      source: "kiosk",
      status: statusFilter.value || undefined,
      keyword: keyword.value.trim() || undefined,
    });
    if (res.code !== 0) return message.error(res.message);
    rows.value = res.data;
    if (statusFilter.value === "pending") {
      pendingCount.value = res.data.length;
    } else {
      const p = await UtilizationAPI.list({ source: "kiosk", status: "pending" });
      if (p.code === 0) pendingCount.value = p.data.length;
    }
  } finally {
    loading.value = false;
  }
}
function switchStatus(v: string) {
  statusFilter.value = v;
  load();
}

// ── 表格 ──────────────────────────────────────────────────────────────────────
const STATUS_META: Record<string, { label: string; type: "default" | "info" | "warning" | "error" | "success" }> = {
  pending: { label: "待审批", type: "warning" },
  processing: { label: "办理中", type: "info" },
  completed: { label: "已办结", type: "success" },
  rejected: { label: "已拒绝", type: "error" },
  cancelled: { label: "已取消", type: "default" },
};

function fmtTime(s?: string | null): string {
  return s ? s.slice(0, 16).replace("T", " ") : "—";
}

const columns: DataTableColumns<UtilApplication> = [
  { title: "登记号", key: "reg_no", width: 150, render: (r) => h("span", { class: "font-mono text-xs" }, r.reg_no) },
  { title: "申请人", key: "applicant_name", width: 100 },
  { title: "电话", key: "phone", width: 120, render: (r) => r.phone || "—" },
  {
    title: "申请码", key: "access_code", width: 90,
    render: (r) => h("code", {
      class: "text-[12px] font-mono px-1.5 py-0.5 rounded",
      style: "background:var(--semi-color-fill-0);color:var(--semi-color-text-1)",
      title: "民众凭此码在自助机查看进度/阅览（遗忘时可告知）",
    }, r.access_code || "—"),
  },
  { title: "申请查看", key: "item_count", width: 84, render: (r) => `${r.item_count} 件` },
  {
    title: "状态", key: "status", width: 90,
    render: (r) => {
      const m = STATUS_META[r.status] ?? STATUS_META.pending;
      return h(NTag, { size: "small", round: true, bordered: false, type: m.type }, { default: () => m.label });
    },
  },
  { title: "查档用途", key: "purpose", minWidth: 140, ellipsis: { tooltip: true }, render: (r) => r.purpose || "—" },
  { title: "提交时间", key: "create_time", width: 130, render: (r) => h("span", { class: "text-[12px] tabular-nums", style: "color:var(--semi-color-text-2)" }, fmtTime(r.create_time)) },
  { title: "经办人", key: "handler_name", width: 96, render: (r) => r.handler_name || "—" },
  {
    title: "操作", key: "actions", width: 250, fixed: "right" as const,
    render: (r) => {
      const buttons = [];
      if (r.status === "pending") {
        buttons.push(
          h(NButton, { size: "tiny", type: "primary", secondary: true, loading: acting.value === r.id, onClick: () => doApprove(r) }, { default: () => "同意查看" }),
          h(NButton, { size: "tiny", tertiary: true, type: "error", onClick: () => openReject(r) }, { default: () => "拒绝" }),
          h(NButton, { size: "tiny", tertiary: true, type: "success", title: "批准并由柜台直接办理", onClick: () => approveAndProcess(r) }, { default: () => "代为办理" }),
        );
      }
      if (r.status === "processing") {
        buttons.push(
          h(NButton, { size: "tiny", type: "primary", tertiary: true, onClick: () => router.push(`/service/reading?app=${r.id}`) }, { default: () => "去办理" }),
          h(NButton, { size: "tiny", tertiary: true, title: "移交其他工作人员（审计留痕）", onClick: () => openTransfer(r.id) }, { default: () => "转办" }),
        );
      }
      buttons.push(h(NButton, { size: "tiny", tertiary: true, onClick: () => openDetail(r.id) }, { default: () => "详情" }));
      return h("div", { class: "flex gap-1.5" }, buttons);
    },
  },
];

// ── 审批动作 ──────────────────────────────────────────────────────────────────
const acting = ref<string | null>(null);

async function doApprove(r: UtilApplication) {
  acting.value = r.id;
  try {
    const res = await UtilizationAPI.approve(r.id);
    if (res.code !== 0) return message.error(res.message);
    message.success(`已批准，民众可在自助机凭申请码 ${r.access_code} 阅览`);
    load();
  } finally {
    acting.value = null;
  }
}

async function approveAndProcess(r: UtilApplication) {
  acting.value = r.id;
  try {
    const res = await UtilizationAPI.approve(r.id);
    if (res.code !== 0) return message.error(res.message);
    router.push(`/service/reading?app=${r.id}`);
  } finally {
    acting.value = null;
  }
}

const rejectShow = ref(false);
const rejectTarget = ref<UtilApplication | null>(null);
const rejectReason = ref("");
function openReject(r: UtilApplication) {
  rejectTarget.value = r;
  rejectReason.value = "";
  rejectShow.value = true;
}
async function doReject() {
  if (!rejectTarget.value) return;
  const res = await UtilizationAPI.reject(rejectTarget.value.id, rejectReason.value);
  if (res.code !== 0) {
    message.error(res.message);
    return false;
  }
  message.info("已拒绝");
  load();
}

// ── 详情 / 转办 ───────────────────────────────────────────────────────────────
const detailShow = ref(false);
const detailId = ref<string | null>(null);
function openDetail(id: string) {
  detailId.value = id;
  detailShow.value = true;
}
const transferShow = ref(false);
const transferId = ref<string | null>(null);
function openTransfer(id: string) {
  transferId.value = id;
  transferShow.value = true;
}

onMounted(load);
onActivated(load);
</script>
