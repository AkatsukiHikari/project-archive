<template>
  <div
    class="bg-[var(--semi-color-bg-0)] rounded-xl border border-[var(--semi-color-border)] shadow-sm p-6 min-h-[500px]"
  >
    <div class="flex justify-between items-center mb-6">
      <h2 class="text-lg font-semibold text-[var(--semi-color-text-0)]">
        租户管理
      </h2>
      <Button theme="solid" type="primary" @click="openCreateModal"
        >新增租户</Button
      >
    </div>
    <Table
      :columns="columns"
      :data-source="data"
      :loading="loading"
      empty-text="暂无内容"
    />

    <!-- 弹窗：新建/编辑租户 -->
    <Modal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑租户' : '新增租户'"
      :confirm-loading="saving"
      @ok="handleModalOk"
      @cancel="modalVisible = false"
    >
      <Form
        class="mt-4"
        :get-form-api="getFormApi"
        :init-values="formData"
        @submit="handleSave"
      >
        <Form.Input
          field="name"
          label="租户名称"
          trigger="blur"
          :rules="[{ required: true, message: '请输入租户名称' }]"
          placeholder="请输入租户名称"
        />
        <Form.Input
          field="code"
          label="租户标识 (Code)"
          trigger="blur"
          :disabled="isEdit"
          :rules="[{ required: true, message: '请输入唯一英文字母标识' }]"
          placeholder="请输入唯一英文字母标识"
        />
        <Form.Input
          field="contact_person"
          label="联系人"
          placeholder="请输入联系人姓名"
        />
        <Form.Input
          field="contact_email"
          label="联系邮箱"
          placeholder="请输入联系邮箱"
        />
        <Form.Input
          field="contact_phone"
          label="联系电话"
          placeholder="请输入联系电话"
        />
      </Form>
    </Modal>
  </div>
</template>

<script setup lang="tsx">
import { ref, onMounted } from "vue";
import { Button, Table, Modal, Toast, Tag, Form } from "@kousum/semi-ui-vue";
import { TenantAPI, type Tenant } from "@/api/iam";

definePageMeta({ layout: "admin", middleware: "auth" });

const loading = ref(false);
const data = ref<Tenant[]>([]);

const columns = [
  { title: "租户名称", dataIndex: "name" },
  { title: "标识 (Code)", dataIndex: "code" },
  { title: "联系人", dataIndex: "contact_person" },
  { title: "联系电话", dataIndex: "contact_phone" },
  {
    title: "状态",
    dataIndex: "is_active",
    render: (val: unknown) => {
      const isActive = val as boolean;
      return (
        <Tag color={isActive ? "green" : "red"}>
          {isActive ? "正常" : "停用"}
        </Tag>
      );
    },
  },
  {
    title: "创建时间",
    dataIndex: "create_time",
    render: (text: unknown) => new Date(text as string).toLocaleString(),
  },
  {
    title: "操作",
    dataIndex: "actions",
    render: (_text: unknown, record: unknown) => {
      const tenant = record as Tenant;
      return (
        <div class="flex gap-2">
          <Button
            theme="borderless"
            type="primary"
            size="small"
            onClick={() => openEditModal(tenant)}
          >
            编辑
          </Button>
          <Button
            theme="borderless"
            type="danger"
            size="small"
            onClick={() => handleDelete(tenant.id)}
          >
            删除
          </Button>
        </div>
      );
    },
  },
];

async function fetchTenants() {
  loading.value = true;
  try {
    const res = (await TenantAPI.list()) as { data?: Tenant[] };
    data.value = res.data || [];
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : "获取租户列表失败";
    Toast.error(msg);
  } finally {
    loading.value = false;
  }
}

onMounted(() => {
  fetchTenants();
});

// -- 表单与弹窗逻辑 --
const modalVisible = ref(false);
const isEdit = ref(false);
const saving = ref(false);
const currentId = ref("");
const formApi = ref<{ submitForm: () => void } | null>(null);

const formData = ref<{
  name: string;
  code: string;
  contact_person: string;
  contact_email: string;
  contact_phone: string;
}>({
  name: "",
  code: "",
  contact_person: "",
  contact_email: "",
  contact_phone: "",
});

function getFormApi(api: { submitForm: () => void }) {
  formApi.value = api;
}

function openCreateModal() {
  isEdit.value = false;
  currentId.value = "";
  formData.value = {
    name: "",
    code: "",
    contact_person: "",
    contact_email: "",
    contact_phone: "",
  };
  modalVisible.value = true;
}

function openEditModal(record: Tenant) {
  isEdit.value = true;
  currentId.value = record.id;
  formData.value = {
    name: record.name || "",
    code: record.code || "",
    contact_person: record.contact_person || "",
    contact_email: record.contact_email || "",
    contact_phone: record.contact_phone || "",
  };
  modalVisible.value = true;
}

function handleModalOk() {
  if (formApi.value) {
    formApi.value.submitForm();
  }
}

async function handleSave(values: Record<string, unknown>) {
  saving.value = true;
  try {
    if (isEdit.value) {
      await TenantAPI.update(currentId.value, values);
      Toast.success("修改成功");
    } else {
      await TenantAPI.create(values);
      Toast.success("创建成功");
    }
    modalVisible.value = false;
    fetchTenants();
  } catch (error: unknown) {
    const msg = error instanceof Error ? error.message : "保存失败";
    Toast.error(msg);
  } finally {
    saving.value = false;
  }
}

function handleDelete(id: string) {
  Modal.warning({
    title: "确认删除",
    content: "删除后不可恢复，确认要删除该租户吗？",
    onOk: async () => {
      try {
        await TenantAPI.delete(id);
        Toast.success("删除成功");
        fetchTenants();
      } catch (error: unknown) {
        const msg = error instanceof Error ? error.message : "删除失败";
        Toast.error(msg);
      }
    },
  });
}
</script>
