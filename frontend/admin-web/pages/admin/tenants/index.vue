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
      @ok="handleSave"
      @cancel="modalVisible = false"
    >
      <div class="flex flex-col gap-4 mt-4">
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >租户名称 <span class="text-red-500">*</span></label
          >
          <Input v-model="formData.name" placeholder="请输入租户名称" />
        </div>
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >租户标识 (Code) <span class="text-red-500">*</span></label
          >
          <Input
            v-model="formData.code"
            :disabled="isEdit"
            placeholder="请输入唯一英文字母标识"
          />
        </div>
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >联系人</label
          >
          <Input
            v-model="formData.contact_person"
            placeholder="请输入联系人姓名"
          />
        </div>
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >联系邮箱</label
          >
          <Input
            v-model="formData.contact_email"
            placeholder="请输入联系邮箱"
          />
        </div>
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >联系电话</label
          >
          <Input
            v-model="formData.contact_phone"
            placeholder="请输入联系电话"
          />
        </div>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="tsx">
import { ref, onMounted } from "vue";
import { definePageMeta } from "#imports";
import { Button, Table, Modal, Input, Toast, Tag } from "@kousum/semi-ui-vue";
import { TenantAPI, type Tenant } from "@/api/iam";

definePageMeta({
  layout: "admin",
});

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
    render: (val: boolean) => (
      <Tag color={val ? "green" : ("red" as any)}>{val ? "正常" : "停用"}</Tag>
    ),
  },
  {
    title: "创建时间",
    dataIndex: "create_time",
    render: (text: string) => new Date(text).toLocaleString(),
  },
  {
    title: "操作",
    dataIndex: "actions",
    render: (_text: unknown, record: Tenant) => (
      <div class="flex gap-2">
        <Button
          theme="borderless"
          type="primary"
          size="small"
          onClick={() => openEditModal(record)}
        >
          编辑
        </Button>
        <Button
          theme="borderless"
          type="danger"
          size="small"
          onClick={() => handleDelete(record.id)}
        >
          删除
        </Button>
      </div>
    ),
  },
];

async function fetchTenants() {
  loading.value = true;
  try {
    const res = (await TenantAPI.list()) as any;
    data.value = res.data || [];
  } catch (error: any) {
    Toast.error(error.message || "获取租户列表失败");
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

async function handleSave() {
  if (!formData.value.name || !formData.value.code) {
    Toast.warning("带 * 号为必填项");
    return;
  }

  saving.value = true;
  try {
    if (isEdit.value) {
      await TenantAPI.update(currentId.value, formData.value);
      Toast.success("修改成功");
    } else {
      await TenantAPI.create(formData.value);
      Toast.success("创建成功");
    }
    modalVisible.value = false;
    fetchTenants();
  } catch (error: any) {
    Toast.error(error.message || "保存失败");
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
      } catch (error: any) {
        Toast.error(error.message || "删除失败");
      }
    },
  });
}
</script>
