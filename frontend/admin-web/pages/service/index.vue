<template>
  <div class="flex flex-col gap-3 min-h-0 flex-1">
    <div class="flex items-start justify-between gap-3">
      <AdminPageHeader
        title="服务工作台"
        description="今日总览、柜台接待与自助机申请审批"
        icon="heroicons:building-storefront"
      />
      <div class="flex items-center gap-2 shrink-0">
        <NButton type="primary" @click="registerShow = true">
          <template #icon><Icon name="heroicons:user-plus" class="w-4 h-4" /></template>
          柜台登记
        </NButton>
        <NButton text size="small" :loading="loading" @click="loadAll">
          <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
          刷新
        </NButton>
      </div>
    </div>

    <!-- ── 今日概览 ─────────────────────────────────────── -->
    <div class="grid grid-cols-2 lg:grid-cols-5 gap-3">
      <div v-for="c in summaryCards" :key="c.label" class="pro-card px-4 py-3 flex items-center gap-3">
        <div
          class="w-9 h-9 rounded-lg flex items-center justify-center shrink-0"
          :style="{ background: `color-mix(in srgb, ${c.color} 12%, transparent)` }"
        >
          <Icon :name="c.icon" class="w-4.5 h-4.5" :style="{ color: c.color }" />
        </div>
        <div class="flex flex-col">
          <span class="text-[20px] font-semibold leading-tight tabular-nums" style="color: var(--semi-color-text-0)">{{ c.value }}</span>
          <span class="text-[11.5px]" style="color: var(--semi-color-text-3)">{{ c.label }}</span>
        </div>
      </div>
    </div>

    <div class="flex gap-3 flex-1 min-h-0 flex-col xl:flex-row">
      <!-- ── 自助机待审批 ─────────────────────────────────── -->
      <div class="pro-card p-4 flex flex-col gap-3 xl:w-[420px] shrink-0 min-h-0">
        <div class="flex items-center gap-2">
          <Icon name="heroicons:computer-desktop" class="w-4.5 h-4.5" style="color: oklch(var(--p))" />
          <span class="text-[14px] font-semibold" style="color: var(--semi-color-text-0)">自助机申请</span>
          <span
            v-if="pendingApps.length"
            class="min-w-[20px] h-5 px-1.5 rounded-full flex items-center justify-center text-[11px] font-bold text-white"
            style="background: var(--semi-color-danger)"
          >{{ pendingApps.length }}</span>
          <div class="flex-1" />
          <span class="text-[11px]" style="color: var(--semi-color-text-3)">15 秒自动刷新</span>
          <NButton text size="tiny" type="primary" @click="router.push('/service/kiosk-apps')">查看全部</NButton>
        </div>

        <div v-if="pendingApps.length === 0" class="flex flex-col items-center gap-2 py-10" style="color: var(--semi-color-text-3)">
          <Icon name="heroicons:check-circle" class="w-8 h-8" />
          <span class="text-[13px]">暂无待审批申请</span>
        </div>

        <div v-else class="flex flex-col gap-2 overflow-y-auto min-h-0">
          <div
            v-for="a in pendingApps"
            :key="a.id"
            class="rounded-lg border px-3 py-2.5 flex flex-col gap-2"
            style="border-color: var(--semi-color-border); background: color-mix(in srgb, var(--semi-color-warning) 4%, transparent)"
          >
            <div class="flex items-center gap-2">
              <PersonAvatar :name="a.applicant_name" :size="32" />
              <div class="flex-1 min-w-0">
                <div class="flex items-center gap-2">
                  <span class="text-[13px] font-medium" style="color: var(--semi-color-text-0)">{{ a.applicant_name }}</span>
                  <span class="text-[11px]" style="color: var(--semi-color-text-3)">{{ a.phone || "—" }}</span>
                </div>
                <div class="text-[11px]" style="color: var(--semi-color-text-3)">
                  {{ a.reg_no }} · 申请查看 {{ a.item_count }} 件 · {{ timeAgo(a.create_time) }}
                </div>
              </div>
              <code class="text-[11px] font-mono px-1.5 py-0.5 rounded" style="background: var(--semi-color-fill-0); color: var(--semi-color-text-2)" :title="'申请码（民众遗忘时可告知）'">{{ a.access_code }}</code>
            </div>
            <div class="flex gap-1.5">
              <NButton size="tiny" type="primary" secondary :loading="acting === a.id" @click="doApprove(a)">同意查看</NButton>
              <NButton size="tiny" tertiary type="error" @click="openReject(a)">拒绝</NButton>
              <NButton size="tiny" tertiary @click="openDetail(a.id)">详情</NButton>
              <div class="flex-1" />
              <NButton size="tiny" tertiary type="success" title="批准并由柜台直接办理" @click="approveAndProcess(a)">代为办理</NButton>
            </div>
          </div>
        </div>
      </div>

      <!-- ── 办理中 ───────────────────────────────────────── -->
      <div class="pro-card p-4 flex-1 min-w-0 min-h-0 flex flex-col gap-3">
        <div class="flex items-center gap-2">
          <Icon name="heroicons:briefcase" class="w-4.5 h-4.5" style="color: oklch(var(--p))" />
          <span class="text-[14px] font-semibold" style="color: var(--semi-color-text-0)">办理中</span>
          <span class="text-[12px]" style="color: var(--semi-color-text-3)">{{ processingApps.length }} 件</span>
        </div>
        <NDataTable
          :columns="processingColumns"
          :data="processingApps"
          :loading="loading"
          :row-key="(r: UtilApplication) => r.id"
          size="small"
          class="flex-1"
        />
      </div>
    </div>

    <!-- 详情抽屉 -->
    <NDrawer v-model:show="detailShow" :width="480" placement="right">
      <NDrawerContent :title="`利用登记详情`" closable>
        <ApplicationDetailPanel :app-id="detailId" @changed="loadAll" @completed="loadAll" />
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

    <!-- 柜台快速登记（与利用申请页同一组件） -->
    <RegisterApplicantModal v-model:show="registerShow" use-type="read" @created="onRegistered" />

    <TransferHandlerModal v-model:show="transferShow" :app-id="transferId" @done="loadAll" />
  </div>
</template>

<script setup lang="tsx">
import { computed, h, onActivated, onBeforeUnmount, onDeactivated, onMounted, ref } from "vue";
import {
  NButton, NDataTable, NDrawer, NDrawerContent, NInput, NModal, NTag, useMessage,
} from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import {
  ApplicationDetailPanel, PersonAvatar, RegisterApplicantModal, TransferHandlerModal,
} from "@/components/archive";
import { UtilizationAPI, type CenterSummary, type UtilApplication } from "@/api/utilization";

definePageMeta({
  layout: "service",
  middleware: "auth",
  breadcrumb: [{ name: "服务工作台", path: "/service" }],
});
useHead({ title: "利用服务中心" });

const router = useRouter();
const message = useMessage();

// ── 数据加载 ──────────────────────────────────────────────────────────────────
const loading = ref(false);
const summary = ref<CenterSummary | null>(null);
const pendingApps = ref<UtilApplication[]>([]);
const processingApps = ref<UtilApplication[]>([]);

async function loadAll() {
  loading.value = true;
  try {
    const [s, pending, processing] = await Promise.all([
      UtilizationAPI.centerSummary(),
      UtilizationAPI.list({ status: "pending", source: "kiosk" }),
      UtilizationAPI.list({ status: "processing" }),
    ]);
    if (s.code === 0) summary.value = s.data;
    if (pending.code === 0) pendingApps.value = pending.data;
    if (processing.code === 0) processingApps.value = processing.data;
  } finally {
    loading.value = false;
  }
}

const summaryCards = computed(() => [
  { label: "今日接待", value: summary.value?.today_total ?? "—", icon: "heroicons:users", color: "oklch(var(--p))" },
  { label: "办理中", value: summary.value?.processing ?? "—", icon: "heroicons:briefcase", color: "var(--semi-color-info)" },
  { label: "待审批", value: summary.value?.pending ?? "—", icon: "heroicons:bell-alert", color: "var(--semi-color-warning)" },
  { label: "今日办结", value: summary.value?.today_completed ?? "—", icon: "heroicons:check-badge", color: "var(--semi-color-success)" },
  { label: "自助机今日", value: summary.value?.kiosk_today ?? "—", icon: "heroicons:computer-desktop", color: "var(--semi-color-text-2)" },
]);

function timeAgo(dateStr: string): string {
  const diff = Date.now() - new Date(dateStr).getTime();
  const m = Math.floor(diff / 60000);
  if (m < 1) return "刚刚";
  if (m < 60) return `${m} 分钟前`;
  const hr = Math.floor(m / 60);
  return hr < 24 ? `${hr} 小时前` : new Date(dateStr).toLocaleDateString("zh-CN");
}

// ── 审批动作 ──────────────────────────────────────────────────────────────────
const acting = ref<string | null>(null);

async function doApprove(a: UtilApplication) {
  acting.value = a.id;
  try {
    const res = await UtilizationAPI.approve(a.id);
    if (res.code !== 0) return message.error(res.message);
    message.success(`已批准，民众可在自助机凭申请码 ${a.access_code} 阅览`);
    loadAll();
  } finally {
    acting.value = null;
  }
}

async function approveAndProcess(a: UtilApplication) {
  acting.value = a.id;
  try {
    const res = await UtilizationAPI.approve(a.id);
    if (res.code !== 0) return message.error(res.message);
    router.push(`/service/reading?app=${a.id}`);
  } finally {
    acting.value = null;
  }
}

const rejectShow = ref(false);
const rejectTarget = ref<UtilApplication | null>(null);
const rejectReason = ref("");

function openReject(a: UtilApplication) {
  rejectTarget.value = a;
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
  loadAll();
}

// ── 办理中表格 ────────────────────────────────────────────────────────────────
const USE_TYPE_LABEL: Record<string, string> = { read: "查阅", borrow: "借阅", copy: "复制", certificate: "出具证明" };

const processingColumns: DataTableColumns<UtilApplication> = [
  { title: "登记号", key: "reg_no", width: 150, render: (r) => h("span", { class: "font-mono text-xs" }, r.reg_no) },
  { title: "利用人", key: "applicant_name", width: 110 },
  {
    title: "来源", key: "source", width: 84,
    render: (r) => h(NTag, { size: "small", round: true, bordered: false, type: r.source === "kiosk" ? "info" : "default" },
      { default: () => (r.source === "kiosk" ? "自助机" : "柜台") }),
  },
  { title: "方式", key: "use_type", width: 90, render: (r) => USE_TYPE_LABEL[r.use_type] ?? r.use_type },
  { title: "调阅", key: "item_count", width: 64, render: (r) => `${r.item_count} 件` },
  { title: "经办人", key: "handler_name", width: 100, render: (r) => r.handler_name || "—" },
  {
    title: "登记时间", key: "create_time", width: 120,
    render: (r) => h("span", { class: "text-[12px] tabular-nums", style: "color:var(--semi-color-text-2)" }, timeAgo(r.create_time)),
  },
  {
    title: "操作", key: "actions", width: 230, fixed: "right" as const,
    render: (r) => h("div", { class: "flex gap-1.5" }, [
      h(NButton, { size: "tiny", type: "primary", tertiary: true, onClick: () => router.push(`/service/reading?app=${r.id}`) }, { default: () => "去办理" }),
      h(NButton, { size: "tiny", tertiary: true, onClick: () => openDetail(r.id) }, { default: () => "详情" }),
      h(NButton, { size: "tiny", tertiary: true, title: "移交其他工作人员（审计留痕）", onClick: () => openTransfer(r.id) }, { default: () => "转办" }),
      h(NButton, { size: "tiny", tertiary: true, type: "success", onClick: () => doComplete(r) }, { default: () => "办结" }),
    ]),
  },
];

async function doComplete(r: UtilApplication) {
  const res = await UtilizationAPI.complete(r.id);
  if (res.code !== 0) return message.error(res.message);
  message.success(`已办结：${r.applicant_name}`);
  loadAll();
}

// ── 详情 / 转办 / 登记 ────────────────────────────────────────────────────────
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

const registerShow = ref(false);
function onRegistered(app: UtilApplication) {
  message.success(`已登记：${app.applicant_name}（${app.reg_no}）`);
  router.push(`/service/reading?app=${app.id}`);
}

// ── 轮询（Tab 保活启停） ──────────────────────────────────────────────────────
let pollTimer: ReturnType<typeof setInterval> | null = null;
function startPolling() {
  stopPolling();
  pollTimer = setInterval(loadAll, 15000);
}
function stopPolling() {
  if (pollTimer) { clearInterval(pollTimer); pollTimer = null; }
}

onMounted(() => { loadAll(); startPolling(); });
onActivated(() => { loadAll(); startPolling(); });
onDeactivated(stopPolling);
onBeforeUnmount(stopPolling);
</script>
