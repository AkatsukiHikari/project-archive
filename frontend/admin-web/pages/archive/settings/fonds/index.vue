<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="全宗管理"
      description="管理档案库全宗（机构档案集合），全宗号全国唯一"
      icon="heroicons:building-library"
    />

    <ProTable
      :columns="columns"
      :data="fondsList"
      :loading="loading"
      empty-content="暂无全宗数据"
      :page-size="0"
    >
      <template #toolbar-right>
        <NButton type="primary" @click="openModal(null)">
          <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
          新增全宗
        </NButton>
      </template>
    </ProTable>

    <CrudModal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑全宗' : '新增全宗'"
      :loading="saving"
      :width="560"
      @confirm="submitForm"
    >
      <NForm ref="formRef" :model="formData" :rules="rules" label-placement="left" :label-width="90">
        <NFormItem path="fonds_code" label="全宗号">
          <NInput v-model:value="formData.fonds_code" :disabled="isEdit" placeholder="如 J001（不可修改）" />
        </NFormItem>
        <NFormItem path="name" label="全宗名称">
          <NInput v-model:value="formData.name" placeholder="机构全称" />
        </NFormItem>
        <NFormItem path="short_name" label="简称">
          <NInput v-model:value="formData.short_name" placeholder="可选" />
        </NFormItem>
        <NFormItem path="retention_period" label="保管期限">
          <NSelect v-model:value="formData.retention_period" :options="retentionOptions" />
        </NFormItem>
        <NFormItem path="status" label="状态">
          <NSelect v-model:value="formData.status" :options="statusOptions" />
        </NFormItem>
        <NFormItem label="起止年度">
          <div class="flex items-center gap-2 w-full">
            <NInputNumber v-model:value="formData.start_year" placeholder="起始年" :min="1900" :max="2099" class="flex-1" />
            <span class="shrink-0 text-gray-400">—</span>
            <NInputNumber v-model:value="formData.end_year" placeholder="截止年（现存不填）" :min="1900" :max="2099" class="flex-1" />
          </div>
        </NFormItem>
        <NFormItem path="description" label="说明">
          <NInput v-model:value="formData.description" type="textarea" :rows="3" placeholder="可选" />
        </NFormItem>
      </NForm>
    </CrudModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, onMounted, reactive } from "vue";
import {
  NButton, NInput, NInputNumber, NSelect, NForm, NFormItem, NTag, NSpace,
  useMessage, useDialog,
} from "naive-ui";
import type { FormInst, DataTableColumns } from "naive-ui";
import { FondsAPI, type Fonds, type FondsCreate, type FondsUpdate } from "@/api/repository";
import AdminPageHeader from "@/components/admin/PageHeader.vue";
import ProTable from "@/components/ui/ProTable.vue";
import CrudModal from "@/components/ui/CrudModal.vue";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();

const fondsList = ref<Fonds[]>([]);
const loading = ref(false);

const retentionOptions = [
  { label: "永久", value: "permanent" },
  { label: "长期", value: "long" },
  { label: "短期", value: "short" },
];

const statusOptions = [
  { label: "在用", value: "active" },
  { label: "归档", value: "archived" },
  { label: "停用", value: "disabled" },
];

const statusColor: Record<string, "success" | "warning" | "default" | "error"> = {
  active: "success", archived: "warning", disabled: "error",
};
const statusLabel: Record<string, string> = { active: "在用", archived: "归档", disabled: "停用" };
const retentionLabel: Record<string, string> = { permanent: "永久", long: "长期", short: "短期" };

const columns: DataTableColumns<Fonds> = [
  { title: "全宗号", key: "fonds_code", width: 110 },
  { title: "全宗名称", key: "name", ellipsis: { tooltip: true } },
  { title: "简称", key: "short_name", width: 120 },
  {
    title: "保管期限",
    key: "retention_period",
    width: 100,
    render: (row) => retentionLabel[row.retention_period] ?? row.retention_period,
  },
  {
    title: "起止年度",
    key: "year_range",
    width: 120,
    render: (row) => `${row.start_year ?? "—"} ~ ${row.end_year ?? "现存"}`,
  },
  {
    title: "状态",
    key: "status",
    width: 90,
    render: (row) => (
      <NTag type={statusColor[row.status] ?? "default"} size="small">
        {statusLabel[row.status] ?? row.status}
      </NTag>
    ),
  },
  {
    title: "操作",
    key: "actions",
    width: 120,
    render: (row) => (
      <NSpace size="small">
        <NButton size="small" onClick={() => openModal(row)}>编辑</NButton>
        <NButton size="small" type="error" onClick={() => confirmDelete(row)}>删除</NButton>
      </NSpace>
    ),
  },
];

const modalVisible = ref(false);
const saving = ref(false);
const isEdit = ref(false);
const editId = ref<string | null>(null);
const formRef = ref<FormInst | null>(null);

const emptyForm = () => ({
  fonds_code: "",
  name: "",
  short_name: "",
  description: "",
  start_year: null as number | null,
  end_year: null as number | null,
  retention_period: "permanent",
  status: "active",
});

const formData = reactive(emptyForm());

const rules = {
  fonds_code: [{ required: true, message: "请输入全宗号", trigger: "blur" }],
  name: [{ required: true, message: "请输入全宗名称", trigger: "blur" }],
  retention_period: [{ required: true, message: "请选择保管期限", trigger: "change" }],
  status: [{ required: true, message: "请选择状态", trigger: "change" }],
};

function openModal(row: Fonds | null) {
  if (row) {
    isEdit.value = true;
    editId.value = row.id;
    Object.assign(formData, {
      fonds_code: row.fonds_code,
      name: row.name,
      short_name: row.short_name ?? "",
      description: row.description ?? "",
      start_year: row.start_year ?? null,
      end_year: row.end_year ?? null,
      retention_period: row.retention_period,
      status: row.status,
    });
  } else {
    isEdit.value = false;
    editId.value = null;
    Object.assign(formData, emptyForm());
  }
  modalVisible.value = true;
}

async function submitForm() {
  await formRef.value?.validate();
  saving.value = true;
  try {
    if (isEdit.value && editId.value) {
      const payload: FondsUpdate = {
        name: formData.name,
        short_name: formData.short_name || undefined,
        description: formData.description || undefined,
        start_year: formData.start_year ?? undefined,
        end_year: formData.end_year ?? undefined,
        retention_period: formData.retention_period,
        status: formData.status,
      };
      await FondsAPI.update(editId.value, payload);
      message.success("已更新");
    } else {
      const payload: FondsCreate = {
        fonds_code: formData.fonds_code,
        name: formData.name,
        short_name: formData.short_name || undefined,
        description: formData.description || undefined,
        start_year: formData.start_year ?? undefined,
        end_year: formData.end_year ?? undefined,
        retention_period: formData.retention_period,
        status: formData.status,
      };
      await FondsAPI.create(payload);
      message.success("已创建");
    }
    modalVisible.value = false;
    await loadList();
  } catch {
    // axios interceptor handles error toast
  } finally {
    saving.value = false;
  }
}

function confirmDelete(row: Fonds) {
  dialog.warning({
    title: "删除确认",
    content: `确定删除全宗「${row.name}」？此操作不可撤销。`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await FondsAPI.remove(row.id);
      message.success("已删除");
      await loadList();
    },
  });
}

async function loadList() {
  loading.value = true;
  try {
    const res = await FondsAPI.list();
    fondsList.value = res.data.data;
  } finally {
    loading.value = false;
  }
}

onMounted(loadList);
</script>
