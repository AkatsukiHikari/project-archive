<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="利用申请"
      description="登记来馆查档人员信息，办理查档与调阅"
      icon="heroicons:document-plus"
    />

    <!-- 工具栏 -->
    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <NSelect v-model:value="filterStatus" :options="statusFilterOptions" style="width: 150px" @update:value="load" />
      <NInput v-model:value="keyword" placeholder="姓名 / 登记号 / 身份证 / 单位" clearable style="width: 240px" @keydown.enter="load">
        <template #prefix><Icon name="heroicons:magnifying-glass" class="w-4 h-4 text-gray-400" /></template>
      </NInput>
      <NButton tertiary @click="load">刷新</NButton>
      <div class="flex-1" />
      <NButton type="primary" @click="openRegister">
        <template #icon><Icon name="heroicons:identification" class="w-4 h-4" /></template>
        登记利用人
      </NButton>
    </div>

    <!-- 列表 -->
    <div class="pro-card p-5">
      <ProTable :columns="columns" :data="rows" :loading="loading" :page-size="15" size="small" />
    </div>

    <!-- 登记利用人 -->
    <NModal v-model:show="showRegister" preset="card" title="登记利用人" style="width: 600px; max-width: 95vw" :mask-closable="false">
      <div class="flex flex-col gap-4">
        <div class="rounded-lg border border-dashed p-3 flex items-center gap-3" style="border-color:var(--semi-color-border)">
          <Icon name="heroicons:identification" class="w-5 h-5" style="color:oklch(var(--p))" />
          <span class="text-[12px]" style="color:var(--semi-color-text-2)">读卡器接入后可一键读取身份证；当前请手动录入</span>
          <div class="flex-1" />
          <NButton size="small" disabled>读取身份证</NButton>
        </div>
        <div class="grid grid-cols-2 gap-4">
          <Field label="姓名" required><NInput v-model:value="form.applicant_name" placeholder="利用人姓名" /></Field>
          <Field label="身份证号"><NInput v-model:value="form.id_card_no" placeholder="身份证号" /></Field>
          <Field label="性别"><NSelect v-model:value="form.gender" :options="genderOptions" placeholder="性别" clearable /></Field>
          <Field label="联系电话"><NInput v-model:value="form.phone" placeholder="联系电话" /></Field>
          <Field label="工作单位" class="col-span-2"><NInput v-model:value="form.organization" placeholder="工作单位" /></Field>
          <Field label="利用方式"><NSelect v-model:value="form.use_type" :options="useTypeOptions" /></Field>
          <Field label="利用目的"><NSelect v-model:value="form.purpose" :options="purposeOptions" placeholder="选择利用目的" clearable filterable tag /></Field>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <NButton @click="showRegister = false">取消</NButton>
          <NButton type="primary" :loading="saving" @click="submitRegister">登记并办理</NButton>
        </div>
      </template>
    </NModal>

    <!-- 详情抽屉（复用组件） -->
    <NDrawer v-model:show="showDetail" :width="480" placement="right">
      <NDrawerContent :title="`利用登记 · ${detailReg}`" closable>
        <ApplicationDetailPanel ref="panelRef" :app-id="detailId" @completed="onChanged" @changed="onChanged" />
      </NDrawerContent>
    </NDrawer>
  </div>
</template>

<script setup lang="tsx">
import { ref, reactive, onMounted, h } from "vue";
import { useRouter } from "vue-router";
import { NSelect, NInput, NButton, NModal, NDrawer, NDrawerContent, NTag, useMessage } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { ApplicationDetailPanel } from "@/components/archive";
import { UtilizationAPI } from "@/api/utilization";
import type { UtilApplication } from "@/api/utilization";
import { DictAPI, dictToOptions } from "@/api/dict";

definePageMeta({
  layout: "service",
  middleware: "auth",
  breadcrumb: [
    { name: "利用服务中心", path: "/service" },
    { name: "利用申请", path: "/service/apply" },
  ],
});

const router = useRouter();
const message = useMessage();

const statusFilterOptions = [
  { label: "办理中", value: "processing" },
  { label: "已办结", value: "completed" },
  { label: "已取消", value: "cancelled" },
  { label: "全部", value: "" },
];
const genderOptions = [{ label: "男", value: "男" }, { label: "女", value: "女" }];
const USE_TYPE_LABEL: Record<string, string> = { read: "查阅", borrow: "借阅", copy: "复制", certificate: "出具证明" };
const STATUS_LABEL: Record<string, string> = { processing: "办理中", completed: "已办结", cancelled: "已取消" };
const STATUS_TONE: Record<string, "info" | "success" | "default"> = { processing: "info", completed: "success", cancelled: "default" };

const Field = (props: { label: string; required?: boolean }, { slots }: { slots: { default?: () => unknown } }) =>
  h("div", { class: "flex flex-col gap-1" }, [
    h("span", { class: "text-sm font-medium" }, [props.label, props.required ? h("span", { class: "text-red-500 ml-0.5" }, "*") : null]),
    slots.default?.(),
  ]);

// ── 字典选项 ──────────────────────────────────────────────────────
const useTypeOptions = ref<{ label: string; value: string }[]>([]);
const purposeOptions = ref<{ label: string; value: string }[]>([]);

// ── 列表 ──────────────────────────────────────────────────────────
const loading = ref(false);
const rows = ref<UtilApplication[]>([]);
const filterStatus = ref("processing");
const keyword = ref("");

async function load() {
  loading.value = true;
  try {
    rows.value = (await UtilizationAPI.list({ status: filterStatus.value || undefined, keyword: keyword.value.trim() || undefined })).data;
  } finally {
    loading.value = false;
  }
}

const fmt = (s?: string | null) => (s ? s.replace("T", " ").slice(0, 16) : "—");

const columns: DataTableColumns<UtilApplication> = [
  { title: "登记号", key: "reg_no", width: 150, render: (r) => h("span", { class: "font-mono text-[12px]" }, r.reg_no) },
  { title: "利用人", key: "applicant_name", width: 100 },
  { title: "身份证号", key: "id_card_no", width: 170, render: (r) => r.id_card_no || "—" },
  { title: "工作单位", key: "organization", minWidth: 140, render: (r) => r.organization || "—" },
  { title: "利用方式", key: "use_type", width: 90, render: (r) => USE_TYPE_LABEL[r.use_type] ?? r.use_type },
  { title: "调阅篮", key: "item_count", width: 80, render: (r) => h("span", { class: "tabular-nums" }, `${r.item_count} 件`) },
  { title: "状态", key: "status", width: 90, render: (r) => h(NTag, { size: "small", type: STATUS_TONE[r.status] ?? "default" }, () => STATUS_LABEL[r.status] ?? r.status) },
  { title: "经办人", key: "handler_name", width: 90, render: (r) => r.handler_name || "—" },
  { title: "登记时间", key: "create_time", width: 140, render: (r) => fmt(r.create_time) },
  {
    title: "操作", key: "actions", width: 200, fixed: "right",
    render: (r) => h("div", { class: "flex gap-2" }, [
      r.status === "processing" ? h(NButton, { size: "small", type: "primary", tertiary: true, onClick: () => goProcess(r) }, () => "去办理") : null,
      r.status === "processing" ? h(NButton, { size: "small", type: "success", tertiary: true, onClick: () => complete(r) }, () => "办理完成") : null,
      h(NButton, { size: "small", tertiary: true, onClick: () => openDetail(r) }, () => "详情"),
    ]),
  },
];

// ── 登记 ──────────────────────────────────────────────────────────
const showRegister = ref(false);
const saving = ref(false);
const form = reactive({
  applicant_name: "", id_card_no: "", gender: null as string | null, phone: "",
  organization: "", use_type: "read", purpose: null as string | null,
});

function openRegister() {
  Object.assign(form, { applicant_name: "", id_card_no: "", gender: null, phone: "", organization: "", use_type: "read", purpose: null });
  showRegister.value = true;
}

async function submitRegister() {
  if (!form.applicant_name.trim()) { message.warning("请填写利用人姓名"); return; }
  saving.value = true;
  try {
    const res = await UtilizationAPI.create({
      applicant_name: form.applicant_name.trim(), id_card_no: form.id_card_no.trim() || null,
      gender: form.gender, phone: form.phone.trim() || null, organization: form.organization.trim() || null,
      use_type: form.use_type, purpose: form.purpose,
    });
    message.success("登记成功，进入查档办理");
    showRegister.value = false;
    router.push(`/service/reading?app=${res.data.id}`);
  } finally {
    saving.value = false;
  }
}

// ── 详情 / 操作 ───────────────────────────────────────────────────
const showDetail = ref(false);
const detailId = ref<string | null>(null);
const detailReg = ref("");

function openDetail(r: UtilApplication) {
  detailId.value = r.id; detailReg.value = r.reg_no; showDetail.value = true;
}
function goProcess(r: UtilApplication) {
  router.push(`/service/reading?app=${r.id}`);
}
async function complete(r: UtilApplication) {
  await UtilizationAPI.complete(r.id);
  message.success("已办理完成");
  await load();
}
function onChanged() { load(); }

onMounted(async () => {
  const [lyfs, lymd] = await Promise.all([DictAPI.listItems("LYFS"), DictAPI.listItems("LYMD")]);
  useTypeOptions.value = dictToOptions(lyfs.data);
  purposeOptions.value = dictToOptions(lymd.data);
  await load();
});
</script>
