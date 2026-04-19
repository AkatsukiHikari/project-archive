<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="租户管理"
      description="多租户隔离配置，管理系统内所有租户"
      icon="heroicons:building-storefront"
    />

    <ProTable :columns="columns" :data="filteredData" :loading="loading" empty-content="暂无租户数据">
      <template #toolbar-left>
        <NInput
          v-model:value="searchText"
          placeholder="搜索租户名称 / 标识…"
          style="width: 240px"
          clearable
        >
          <template #prefix><Icon name="heroicons:magnifying-glass" class="w-4 h-4" /></template>
        </NInput>
        <NSelect
          v-model:value="filterStatus"
          :options="statusOptions"
          style="width: 110px"
          placeholder="状态"
        />
      </template>
      <template #toolbar-right>
        <NButton type="primary" @click="openModal(null)">
          <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
          新增租户
        </NButton>
      </template>
    </ProTable>

    <CrudModal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑租户' : '新增租户'"
      :loading="saving"
      :width="480"
      @confirm="submitForm"
    >
      <NForm ref="formRef" :model="formData" :rules="formRules" label-placement="left" :label-width="80">
        <NFormItem path="name" label="租户名称">
          <NInput v-model:value="formData.name" placeholder="请输入租户名称" />
        </NFormItem>
        <NFormItem path="code" label="租户标识">
          <NInput v-model:value="formData.code" :disabled="isEdit" placeholder="例如：acme（创建后不可修改）" />
        </NFormItem>
        <NFormItem path="contact_person" label="联系人">
          <NInput v-model:value="formData.contact_person" placeholder="可选" />
        </NFormItem>
        <NFormItem path="contact_email" label="联系邮箱">
          <NInput v-model:value="formData.contact_email" placeholder="可选" />
        </NFormItem>
        <NFormItem path="contact_phone" label="联系电话">
          <NInput v-model:value="formData.contact_phone" placeholder="可选" />
        </NFormItem>
        <NFormItem path="description" label="描述">
          <NInput v-model:value="formData.description" placeholder="可选" />
        </NFormItem>
      </NForm>
    </CrudModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted, reactive } from "vue";
import { NButton, NInput, NSelect, NForm, NFormItem, NTag, useMessage, useDialog } from "naive-ui";
import type { FormInst } from "naive-ui";
import { TenantAPI, type Tenant } from "@/api/iam";
import AdminPageHeader from "@/components/admin/PageHeader.vue";
import ProTable from "@/components/ui/ProTable.vue";
import CrudModal from "@/components/ui/CrudModal.vue";

definePageMeta({ layout: "admin", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();

// ── 数据 ──────────────────────────────────────────────────────────
const data = ref<Tenant[]>([]);
const loading = ref(false);
const searchText = ref("");
const filterStatus = ref<string | null>(null);

const statusOptions = [
  { label: "全部", value: "" },
  { label: "正常", value: "active" },
  { label: "停用", value: "suspended" },
];

const filteredData = computed(() => {
  let list = data.value;
  if (searchText.value) {
    const q = searchText.value.toLowerCase();
    list = list.filter(
      (t) => t.name.toLowerCase().includes(q) || t.code.toLowerCase().includes(q),
    );
  }
  if (filterStatus.value) list = list.filter((t) => t.status === filterStatus.value);
  return list;
});

onMounted(fetchTenants);

async function fetchTenants() {
  loading.value = true;
  try {
    const res = (await TenantAPI.list()) as any;
    data.value = res.data ?? [];
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "获取租户列表失败");
  } finally {
    loading.value = false;
  }
}

// ── 表格列 ────────────────────────────────────────────────────────
const STATUS_MAP: Record<string, { type: "success" | "error" | "default"; label: string }> = {
  active:    { type: "success", label: "正常" },
  suspended: { type: "error",   label: "停用" },
  archived:  { type: "default", label: "归档" },
};

const columns = [
  {
    title: "租户",
    key: "name",
    render: (row: Tenant) => (
      <div class="flex items-center gap-2.5 py-1">
        <div
          class="w-8 h-8 rounded-lg flex items-center justify-center text-sm font-bold shrink-0"
          style="background:var(--semi-color-primary-light-default);color:var(--semi-color-primary)"
        >
          {row.name.slice(0, 1)}
        </div>
        <div>
          <div class="text-[13px] font-medium" style="color:var(--semi-color-text-0)">{row.name}</div>
          <div class="text-[11px] font-mono" style="color:var(--semi-color-text-2)">{row.code}</div>
        </div>
      </div>
    ),
  },
  {
    title: "联系人", key: "contact_person", width: 120,
    render: (row: Tenant) => row.contact_person || <span style="color:var(--semi-color-text-3)">—</span>,
  },
  {
    title: "联系邮箱", key: "contact_email",
    render: (row: Tenant) => row.contact_email
      ? <span class="text-[12px]" style="color:var(--semi-color-text-1)">{row.contact_email}</span>
      : <span style="color:var(--semi-color-text-3)">—</span>,
  },
  {
    title: "联系电话", key: "contact_phone", width: 130,
    render: (row: Tenant) => row.contact_phone || <span style="color:var(--semi-color-text-3)">—</span>,
  },
  {
    title: "状态", key: "status", width: 90,
    render: (row: Tenant) => {
      const cfg = STATUS_MAP[row.status] ?? { type: "default" as const, label: row.status };
      return <NTag type={cfg.type} size="small">{cfg.label}</NTag>;
    },
  },
  {
    title: "创建时间", key: "create_time", width: 130,
    render: (row: Tenant) => (
      <span class="text-[12px]" style="color:var(--semi-color-text-2)">
        {new Date(row.create_time).toLocaleDateString("zh-CN")}
      </span>
    ),
  },
  {
    title: "操作", key: "_actions", width: 120,
    render: (row: Tenant) => (
      <div class="flex gap-1">
        <NButton text type="primary" size="small" onClick={() => openModal(row)}>编辑</NButton>
        <NButton text type="error" size="small" onClick={() => handleDelete(row.id)}>删除</NButton>
      </div>
    ),
  },
];

// ── 新增 / 编辑 modal ─────────────────────────────────────────────
const modalVisible = ref(false);
const isEdit = ref(false);
const saving = ref(false);
const currentId = ref("");
const formRef = ref<FormInst | null>(null);

const formData = reactive({
  name: "", code: "", contact_person: "", contact_email: "", contact_phone: "", description: "",
});

const formRules = {
  name: [{ required: true, message: "请输入租户名称", trigger: "blur" }],
  code: [{ required: true, message: "请输入唯一标识", trigger: "blur" }],
};

function submitForm() {
  formRef.value?.validate((errors) => {
    if (!errors) handleSave();
  });
}

function openModal(record: Tenant | null) {
  if (record) {
    isEdit.value = true;
    currentId.value = record.id;
    Object.assign(formData, {
      name: record.name, code: record.code,
      contact_person: record.contact_person ?? "",
      contact_email: record.contact_email ?? "",
      contact_phone: record.contact_phone ?? "",
      description: record.description ?? "",
    });
  } else {
    isEdit.value = false;
    currentId.value = "";
    Object.assign(formData, { name: "", code: "", contact_person: "", contact_email: "", contact_phone: "", description: "" });
  }
  modalVisible.value = true;
}

async function handleSave() {
  saving.value = true;
  try {
    if (isEdit.value) {
      await TenantAPI.update(currentId.value, { ...formData });
      message.success("更新成功");
    } else {
      await TenantAPI.create({ ...formData });
      message.success("创建成功");
    }
    modalVisible.value = false;
    fetchTenants();
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "保存失败");
  } finally {
    saving.value = false;
  }
}

function handleDelete(id: string) {
  dialog.warning({
    title: "确认删除该租户？",
    content: "删除后不可恢复，租户下的所有数据将受影响，确认继续吗？",
    positiveText: "确认删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await TenantAPI.delete(id);
        message.success("删除成功");
        fetchTenants();
      } catch (err: unknown) {
        message.error(err instanceof Error ? err.message : "删除失败");
      }
    },
  });
}
</script>
