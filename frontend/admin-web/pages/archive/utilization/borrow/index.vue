<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader title="借阅管理" description="档案借阅登记、借出、归还与续借，逾期自动标记" icon="heroicons:arrow-uturn-right" />

    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <NSelect v-model:value="bizFilter" :options="bizOptions" placeholder="全部状态" clearable style="width: 150px" @update:value="load" />
      <NInput v-model:value="keyword" placeholder="借阅人 / 登记号 / 单位" clearable style="width: 220px" @keydown.enter="load">
        <template #prefix><Icon name="heroicons:magnifying-glass" class="w-4 h-4 text-gray-400" /></template>
      </NInput>
      <NButton tertiary @click="load">刷新</NButton>
      <div class="flex-1" />
      <NButton type="primary" @click="showRegister = true">
        <template #icon><Icon name="heroicons:identification" class="w-4 h-4" /></template>
        登记借阅
      </NButton>
    </div>

    <div class="pro-card p-5">
      <ProTable :columns="columns" :data="filteredRows" :loading="loading" :page-size="15" size="small" />
    </div>

    <RegisterApplicantModal v-model:show="showRegister" use-type="borrow" @created="onRegistered" />

    <NDrawer v-model:show="showDetail" :width="480" placement="right">
      <NDrawerContent :title="`借阅登记 · ${detailReg}`" closable>
        <ApplicationDetailPanel :app-id="detailId" :show-actions="false" />
      </NDrawerContent>
    </NDrawer>

    <!-- 借出 / 续借 -->
    <NModal v-model:show="showLend" preset="dialog" :title="lendMode === 'lend' ? '办理借出' : '续借'">
      <div class="flex flex-col gap-2 pt-2">
        <span class="text-sm" style="color:var(--semi-color-text-2)">应还日期</span>
        <NDatePicker v-model:value="dueTs" type="date" format="yyyy-MM-dd" style="width: 100%" />
      </div>
      <template #action>
        <NButton @click="showLend = false">取消</NButton>
        <NButton type="primary" :loading="acting" @click="confirmLend">确定</NButton>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted, h } from "vue";
import { useRouter } from "vue-router";
import { NSelect, NInput, NButton, NTag, NModal, NDatePicker, NDrawer, NDrawerContent, useMessage, useDialog } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { RegisterApplicantModal, ApplicationDetailPanel } from "@/components/archive";
import { UtilizationAPI } from "@/api/utilization";
import type { UtilApplication } from "@/api/utilization";

definePageMeta({ layout: "archive", middleware: "auth" });

const router = useRouter();
const message = useMessage();
const dialog = useDialog();

const bizOptions = [
  { label: "待借出", value: "待借出" }, { label: "借出中", value: "借出中" },
  { label: "逾期", value: "逾期" }, { label: "已归还", value: "已归还" },
];
const BIZ_TONE: Record<string, "default" | "info" | "error" | "success"> = {
  待借出: "default", 借出中: "info", 逾期: "error", 已归还: "success",
};

const loading = ref(false);
const rows = ref<UtilApplication[]>([]);
const bizFilter = ref<string | null>(null);
const keyword = ref("");
const filteredRows = computed(() => bizFilter.value ? rows.value.filter((r) => r.biz_status === bizFilter.value) : rows.value);

async function load() {
  loading.value = true;
  try {
    rows.value = (await UtilizationAPI.list({ use_type: "borrow", keyword: keyword.value.trim() || undefined })).data;
  } finally {
    loading.value = false;
  }
}

const fmt = (s?: string | null) => (s ? s.slice(0, 10) : "—");

const columns: DataTableColumns<UtilApplication> = [
  { title: "登记号", key: "reg_no", width: 150, render: (r) => h("span", { class: "font-mono text-[12px]" }, r.reg_no) },
  { title: "借阅人", key: "applicant_name", width: 90 },
  { title: "工作单位", key: "organization", minWidth: 130, render: (r) => r.organization || "—" },
  { title: "调阅篮", key: "item_count", width: 70, render: (r) => `${r.item_count} 件` },
  { title: "状态", key: "biz_status", width: 90, render: (r) => h(NTag, { size: "small", type: BIZ_TONE[r.biz_status ?? ""] ?? "default" }, () => r.biz_status ?? "—") },
  { title: "借出日期", key: "borrowed_at", width: 110, render: (r) => fmt(r.borrowed_at) },
  { title: "应还日期", key: "due_date", width: 110, render: (r) => h("span", { class: r.biz_status === "逾期" ? "text-red-500" : "" }, fmt(r.due_date)) },
  {
    title: "操作", key: "actions", width: 220, fixed: "right",
    render: (r) => {
      const btns = [];
      if (r.biz_status === "待借出") {
        btns.push(h(NButton, { size: "small", tertiary: true, onClick: () => goProcess(r) }, () => "选档"));
        btns.push(h(NButton, { size: "small", type: "primary", tertiary: true, onClick: () => openLend(r, "lend") }, () => "借出"));
      } else if (r.biz_status === "借出中" || r.biz_status === "逾期") {
        btns.push(h(NButton, { size: "small", tertiary: true, onClick: () => openLend(r, "renew") }, () => "续借"));
        btns.push(h(NButton, { size: "small", type: "success", tertiary: true, onClick: () => doReturn(r) }, () => "归还"));
      }
      btns.push(h(NButton, { size: "small", tertiary: true, onClick: () => openDetail(r) }, () => "详情"));
      return h("div", { class: "flex gap-2" }, btns);
    },
  },
];

// ── 登记 / 选档 ───────────────────────────────────────────────────
const showRegister = ref(false);
function onRegistered(app: UtilApplication) { router.push(`/archive/utilization/reading?app=${app.id}`); }
function goProcess(r: UtilApplication) { router.push(`/archive/utilization/reading?app=${r.id}`); }

// ── 借出 / 续借 ───────────────────────────────────────────────────
const showLend = ref(false);
const lendMode = ref<"lend" | "renew">("lend");
const lendTarget = ref<UtilApplication | null>(null);
const dueTs = ref<number | null>(Date.now() + 30 * 86400000);
const acting = ref(false);

function openLend(r: UtilApplication, mode: "lend" | "renew") {
  lendTarget.value = r; lendMode.value = mode;
  dueTs.value = r.due_date ? new Date(r.due_date).getTime() : Date.now() + 30 * 86400000;
  showLend.value = true;
}
async function confirmLend() {
  if (!lendTarget.value || !dueTs.value) { message.warning("请选择应还日期"); return; }
  const d = new Date(dueTs.value);
  const due = `${d.getFullYear()}-${String(d.getMonth() + 1).padStart(2, "0")}-${String(d.getDate()).padStart(2, "0")}`;
  acting.value = true;
  try {
    if (lendMode.value === "lend") await UtilizationAPI.lend(lendTarget.value.id, due);
    else await UtilizationAPI.renew(lendTarget.value.id, due);
    message.success(lendMode.value === "lend" ? "已办理借出" : "已续借");
    showLend.value = false;
    await load();
  } finally {
    acting.value = false;
  }
}

function doReturn(r: UtilApplication) {
  dialog.success({
    title: "办理归还", content: `确认「${r.applicant_name}」归还本次借阅（${r.item_count} 件）？`,
    positiveText: "确认归还", negativeText: "取消",
    onPositiveClick: async () => { await UtilizationAPI.returnBorrow(r.id); message.success("已归还"); await load(); },
  });
}

// ── 详情 ──────────────────────────────────────────────────────────
const showDetail = ref(false);
const detailId = ref<string | null>(null);
const detailReg = ref("");
function openDetail(r: UtilApplication) { detailId.value = r.id; detailReg.value = r.reg_no; showDetail.value = true; }

onMounted(load);
</script>
