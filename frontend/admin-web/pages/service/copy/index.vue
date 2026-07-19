<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader title="复制申请" description="档案复制登记与办理（扫描 / 复印 / 拍照），记录份数与费用" icon="heroicons:document-duplicate" />

    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <NSelect v-model:value="bizFilter" :options="bizOptions" placeholder="全部状态" clearable style="width: 140px" @update:value="load" />
      <NInput v-model:value="keyword" placeholder="申请人 / 登记号 / 单位" clearable style="width: 220px" @keydown.enter="load">
        <template #prefix><Icon name="heroicons:magnifying-glass" class="w-4 h-4 text-gray-400" /></template>
      </NInput>
      <NButton tertiary @click="load">刷新</NButton>
      <div class="flex-1" />
      <NButton type="primary" @click="showRegister = true">
        <template #icon><Icon name="heroicons:identification" class="w-4 h-4" /></template>
        登记复制
      </NButton>
    </div>

    <div class="pro-card p-5">
      <ProTable :columns="columns" :data="filteredRows" :loading="loading" :page-size="15" size="small" />
    </div>

    <RegisterApplicantModal v-model:show="showRegister" use-type="copy" @created="onRegistered" />

    <NDrawer v-model:show="showDetail" :width="480" placement="right">
      <NDrawerContent :title="`复制登记 · ${detailReg}`" closable>
        <ApplicationDetailPanel :app-id="detailId" :show-actions="false" />
      </NDrawerContent>
    </NDrawer>

    <NModal v-model:show="showCopy" preset="dialog" title="办理复制">
      <div class="flex flex-col gap-3 pt-2">
        <div class="flex flex-col gap-1">
          <span class="text-sm" style="color:var(--semi-color-text-2)">复制方式</span>
          <NSelect v-model:value="copyForm.method" :options="methodOptions" />
        </div>
        <div class="grid grid-cols-2 gap-3">
          <div class="flex flex-col gap-1">
            <span class="text-sm" style="color:var(--semi-color-text-2)">份数</span>
            <NInputNumber v-model:value="copyForm.copies" :min="1" class="w-full" />
          </div>
          <div class="flex flex-col gap-1">
            <span class="text-sm" style="color:var(--semi-color-text-2)">费用（元）</span>
            <NInputNumber v-model:value="copyForm.fee" :min="0" :precision="2" class="w-full" />
          </div>
        </div>
      </div>
      <template #action>
        <NButton @click="showCopy = false">取消</NButton>
        <NButton type="primary" :loading="acting" @click="confirmCopy">确认交付</NButton>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, reactive, computed, onMounted, h } from "vue";
import { useRouter } from "vue-router";
import { NSelect, NInput, NInputNumber, NButton, NTag, NModal, NDrawer, NDrawerContent, useMessage } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { RegisterApplicantModal, ApplicationDetailPanel } from "@/components/archive";
import { UtilizationAPI } from "@/api/utilization";
import type { UtilApplication } from "@/api/utilization";

definePageMeta({
  layout: "service",
  middleware: "auth",
  breadcrumb: [
    { name: "利用服务中心", path: "/service" },
    { name: "复制申请", path: "/service/copy" },
  ],
});

const router = useRouter();
const message = useMessage();

const bizOptions = [{ label: "待复制", value: "待复制" }, { label: "已交付", value: "已交付" }];
const methodOptions = [{ label: "扫描件", value: "scan" }, { label: "复印件", value: "photocopy" }, { label: "拍照", value: "photo" }];
const METHOD_LABEL: Record<string, string> = { scan: "扫描件", photocopy: "复印件", photo: "拍照" };
const BIZ_TONE: Record<string, "default" | "success"> = { 待复制: "default", 已交付: "success" };

const loading = ref(false);
const rows = ref<UtilApplication[]>([]);
const bizFilter = ref<string | null>(null);
const keyword = ref("");
const filteredRows = computed(() => bizFilter.value ? rows.value.filter((r) => r.biz_status === bizFilter.value) : rows.value);

async function load() {
  loading.value = true;
  try {
    rows.value = (await UtilizationAPI.list({ use_type: "copy", keyword: keyword.value.trim() || undefined })).data;
  } finally {
    loading.value = false;
  }
}

const columns: DataTableColumns<UtilApplication> = [
  { title: "登记号", key: "reg_no", width: 150, render: (r) => h("span", { class: "font-mono text-[12px]" }, r.reg_no) },
  { title: "申请人", key: "applicant_name", width: 90 },
  { title: "工作单位", key: "organization", minWidth: 130, render: (r) => r.organization || "—" },
  { title: "调阅篮", key: "item_count", width: 70, render: (r) => `${r.item_count} 件` },
  { title: "状态", key: "biz_status", width: 90, render: (r) => h(NTag, { size: "small", type: BIZ_TONE[r.biz_status ?? ""] ?? "default" }, () => r.biz_status ?? "—") },
  { title: "复制方式", key: "copy_method", width: 90, render: (r) => (r.copy_method ? METHOD_LABEL[r.copy_method] ?? r.copy_method : "—") },
  { title: "份数", key: "copies", width: 70, render: (r) => r.copies ?? "—" },
  { title: "费用", key: "fee", width: 90, render: (r) => (r.fee != null ? `¥${Number(r.fee).toFixed(2)}` : "—") },
  {
    title: "操作", key: "actions", width: 170, fixed: "right",
    render: (r) => {
      const btns = [];
      if (r.biz_status === "待复制") {
        btns.push(h(NButton, { size: "small", tertiary: true, onClick: () => goProcess(r) }, () => "选档"));
        btns.push(h(NButton, { size: "small", type: "primary", tertiary: true, onClick: () => openCopy(r) }, () => "办理复制"));
      }
      btns.push(h(NButton, { size: "small", tertiary: true, onClick: () => openDetail(r) }, () => "详情"));
      return h("div", { class: "flex gap-2" }, btns);
    },
  },
];

const showRegister = ref(false);
function onRegistered(app: UtilApplication) { router.push(`/service/reading?app=${app.id}`); }
function goProcess(r: UtilApplication) { router.push(`/service/reading?app=${r.id}`); }

// ── 办理复制 ──────────────────────────────────────────────────────
const showCopy = ref(false);
const copyTarget = ref<UtilApplication | null>(null);
const acting = ref(false);
const copyForm = reactive({ method: "scan", copies: 1, fee: 0 });

function openCopy(r: UtilApplication) {
  copyTarget.value = r;
  Object.assign(copyForm, { method: "scan", copies: r.item_count || 1, fee: 0 });
  showCopy.value = true;
}
async function confirmCopy() {
  if (!copyTarget.value) return;
  acting.value = true;
  try {
    await UtilizationAPI.processCopy(copyTarget.value.id, { copy_method: copyForm.method, copies: copyForm.copies, fee: copyForm.fee });
    message.success("已办理复制并交付");
    showCopy.value = false;
    await load();
  } finally {
    acting.value = false;
  }
}

// ── 详情 ──────────────────────────────────────────────────────────
const showDetail = ref(false);
const detailId = ref<string | null>(null);
const detailReg = ref("");
function openDetail(r: UtilApplication) { detailId.value = r.id; detailReg.value = r.reg_no; showDetail.value = true; }

onMounted(load);
</script>
