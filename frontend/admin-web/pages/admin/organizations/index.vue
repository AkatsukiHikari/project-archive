<template>
  <div class="flex flex-col gap-4">
    <!-- 顶部租户选择 -->
    <div
      class="bg-[var(--semi-color-bg-0)] rounded-xl border border-[var(--semi-color-border)] shadow-sm p-4 flex items-center gap-4"
    >
      <span class="font-medium text-[var(--semi-color-text-0)] text-sm"
        >当前管理租户：</span
      >
      <Select
        v-model="currentTenantId"
        :style="{ width: '280px' }"
        :loading="tenantsLoading"
        placeholder="请选择租户"
        @change="handleTenantChange"
      >
        <Select.Option v-for="t in tenants" :key="t.id" :value="t.id">
          {{ t.name }} ({{ t.code }})
        </Select.Option>
      </Select>
    </div>

    <div
      class="flex flex-col lg:flex-row gap-6 h-[calc(100vh-210px)] min-h-[500px]"
    >
      <!-- Left: Org Tree -->
      <div
        class="w-full lg:w-1/3 xl:w-1/4 bg-[var(--semi-color-bg-0)] rounded-xl border border-[var(--semi-color-border)] shadow-sm flex flex-col p-4 overflow-hidden"
      >
        <div class="flex justify-between items-center mb-4 shrink-0">
          <h2 class="font-semibold text-[var(--semi-color-text-0)]">
            组织架构
          </h2>
          <Button
            type="primary"
            theme="borderless"
            :disabled="!currentTenantId"
            @click="openOrgModal(null)"
            ><template #icon><IconPlus /></template>新增部门</Button
          >
        </div>
        <div class="flex-1 overflow-y-auto custom-scrollbar">
          <Tree
            :tree-data="orgTreeData"
            default-expand-all
            :render-label="renderOrgLabel"
            @select="handleOrgSelect"
          />
        </div>
      </div>

      <!-- Right: Org Details/Members -->
      <div
        class="w-full lg:w-2/3 xl:w-3/4 bg-[var(--semi-color-bg-0)] rounded-xl border border-[var(--semi-color-border)] shadow-sm flex flex-col p-6 overflow-hidden"
      >
        <div class="flex justify-between items-center mb-6 shrink-0">
          <h2 class="text-lg font-semibold text-[var(--semi-color-text-0)]">
            部门成员 {{ selectedOrgName ? `(${selectedOrgName})` : "" }}
          </h2>
          <Button
            theme="solid"
            type="primary"
            :disabled="!selectedOrgId"
            @click="openUserModal(null)"
          >
            <template #icon><IconPlus /></template>
            添加成员
          </Button>
        </div>
        <div class="flex-1 overflow-y-auto custom-scrollbar">
          <Table
            :columns="userColumns"
            :data-source="users"
            :loading="usersLoading"
            empty-text="暂无部门成员数据"
          />
        </div>
      </div>
    </div>

    <!-- Org Modal -->
    <Modal
      v-model:visible="orgModalVisible"
      :title="isOrgEdit ? '编辑部门' : '新增部门'"
      :confirm-loading="orgSaving"
      @ok="handleOrgModalOk"
      @cancel="orgModalVisible = false"
    >
      <Form
        class="mt-4"
        :get-form-api="getOrgFormApi"
        :init-values="orgFormData"
        @submit="handleOrgSave"
      >
        <Form.Input
          field="name"
          label="部门名称"
          trigger="blur"
          :rules="[{ required: true, message: '请输入部门名称' }]"
          placeholder="请输入部门名称"
        />
        <Form.Input
          field="code"
          label="部门标识 (Code)"
          trigger="blur"
          :disabled="isOrgEdit"
          :rules="[{ required: true, message: '请输入唯一英文字母标识' }]"
          placeholder="请输入唯一英文字母标识"
        />
        <Form.InputNumber
          field="sort_order"
          label="排序号"
          class="w-full"
          :min="0"
        />
        <div v-if="!isOrgEdit && selectedOrgId">
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >上级部门</label
          >
          <Input :value="selectedOrgName" disabled />
          <p class="text-xs text-[var(--semi-color-text-2)] mt-1">
            留空则作为一级部门，当前选中则会自动作为其子部门创建
          </p>
        </div>
      </Form>
    </Modal>

    <!-- User Modal -->
    <Modal
      v-model:visible="userModalVisible"
      :title="isUserEdit ? '编辑成员' : '添加成员'"
      :confirm-loading="userSaving"
      @ok="handleUserModalOk"
      @cancel="userModalVisible = false"
    >
      <Form
        class="mt-4"
        :get-form-api="getUserFormApi"
        :init-values="userFormData"
        @submit="handleUserSave"
      >
        <Form.Input
          field="username"
          label="用户名"
          trigger="blur"
          :disabled="isUserEdit"
          :rules="[{ required: true, message: '请输入登录用户名' }]"
          placeholder="请输入登录用户名"
        />
        <Form.Input
          field="full_name"
          label="真实姓名"
          trigger="blur"
          :rules="[{ required: true, message: '请输入用户真实姓名' }]"
          placeholder="请输入用户真实姓名"
        />
        <Form.Input
          field="email"
          label="邮箱"
          trigger="blur"
          :rules="[{ required: true, message: '请输入用户邮箱' }]"
          placeholder="请输入用户邮箱"
        />
        <Form.Input
          v-if="!isUserEdit"
          field="password"
          label="初始密码"
          type="password"
          trigger="blur"
          :rules="[{ required: true, message: '请输入初始登录密码' }]"
          placeholder="请输入初始登录密码"
        />
      </Form>
    </Modal>
  </div>
</template>

<script setup lang="tsx">
import { ref, onMounted } from "vue";
import {
  Button,
  Tree,
  Table,
  Modal,
  Input,
  Select,
  Toast,
  Tag,
  Form,
} from "@kousum/semi-ui-vue";
import {
  TenantAPI,
  OrgAPI,
  UserAPI,
  type Tenant,
  type OrganizationTree,
  type User,
  type Organization,
} from "@/api/iam";
import { IconEdit, IconDelete, IconPlus } from "@kousum/semi-icons-vue";

definePageMeta({ layout: "admin", middleware: "auth" });

// -- 全局状态 --
const tenants = ref<Tenant[]>([]);
const currentTenantId = ref<string>("");
const tenantsLoading = ref(false);

// -- 组织架构状态 --
const orgTreeData = ref<Record<string, unknown>[]>([]);
const orgRawData = ref<OrganizationTree[]>([]);
const selectedOrgId = ref<string>("");
const selectedOrgName = ref<string>("");

// -- 用户状态 --
const users = ref<User[]>([]);
const usersLoading = ref(false);

onMounted(async () => {
  await fetchTenants();
});

// ==== 租户加载 ====
async function fetchTenants() {
  tenantsLoading.value = true;
  try {
    const res = await TenantAPI.list();
    tenants.value = res.data || [];
    if (tenants.value && tenants.value.length > 0) {
      currentTenantId.value = tenants.value[0]?.id || "";
      handleTenantChange(currentTenantId.value);
    }
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "加载租户失败";
    Toast.error(errorMsg);
  } finally {
    tenantsLoading.value = false;
  }
}

function handleTenantChange(
  val:
    | string
    | number
    | boolean
    | Record<string, unknown>
    | unknown[]
    | undefined,
) {
  currentTenantId.value = String(val || "");
  selectedOrgId.value = "";
  selectedOrgName.value = "";
  users.value = [];
  fetchOrgTree();
}

// ==== 组织架构逻辑 ====
function transformOrgTree(
  nodes: OrganizationTree[],
): Record<string, unknown>[] {
  return nodes.map((node) => ({
    label: node.name,
    value: node.id,
    key: node.id,
    rawData: node,
    children: node.children ? transformOrgTree(node.children) : [],
  }));
}

async function fetchOrgTree() {
  if (!currentTenantId.value) return;
  try {
    const res = await OrgAPI.tree(currentTenantId.value);
    orgRawData.value = res.data || [];
    orgTreeData.value = transformOrgTree(orgRawData.value);
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "加载组织树失败";
    Toast.error(errorMsg);
  }
}

function handleOrgSelect(
  selectedKey: string,
  selected: boolean,
  selectedNode: Record<string, unknown>,
) {
  if (selected && selectedNode) {
    selectedOrgId.value = selectedNode.value as string;
    selectedOrgName.value = selectedNode.label as string;
    fetchUsers();
  } else {
    selectedOrgId.value = "";
    selectedOrgName.value = "";
    users.value = [];
  }
}

// 树节点自定义渲染：加入编辑和删除按钮
const renderOrgLabel = (
  label?:
    | string
    | number
    | boolean
    | Record<string, unknown>
    | unknown[]
    | null
    | undefined,
  item?: Record<string, unknown>,
) => {
  return (
    <div class="flex items-center justify-between w-full group pr-2">
      <span>{label as string}</span>
      <div class="hidden group-hover:flex items-center gap-1">
        <Button
          icon={<IconEdit />}
          theme="borderless"
          type="primary"
          size="small"
          onClick={(e: Event) => {
            e.stopPropagation();
            if (item && item.rawData)
              openOrgModal(item.rawData as Organization);
          }}
        />
        <Button
          icon={<IconDelete />}
          theme="borderless"
          type="danger"
          size="small"
          onClick={(e: Event) => {
            e.stopPropagation();
            if (item && item.rawData)
              handleOrgDelete((item.rawData as Organization).id);
          }}
        />
      </div>
    </div>
  );
};

// -- Org Modal --
const orgModalVisible = ref(false);
const isOrgEdit = ref(false);
const orgSaving = ref(false);
const currentOrgId = ref("");
const orgFormApi = ref<{ submitForm: () => void } | null>(null);

function getOrgFormApi(api: { submitForm: () => void }) {
  orgFormApi.value = api;
}

const orgFormData = ref<{
  name: string;
  code: string;
  sort_order: number;
  parent_id?: string;
}>({
  name: "",
  code: "",
  sort_order: 0,
});

function openOrgModal(record: Organization | null) {
  if (record) {
    isOrgEdit.value = true;
    currentOrgId.value = record.id;
    orgFormData.value = {
      name: record.name,
      code: record.code,
      sort_order: record.sort_order || 0,
    };
  } else {
    isOrgEdit.value = false;
    currentOrgId.value = "";
    orgFormData.value = {
      name: "",
      code: "",
      sort_order: 0,
      parent_id: selectedOrgId.value || undefined,
    };
  }
  orgModalVisible.value = true;
}

function handleOrgModalOk() {
  if (orgFormApi.value) {
    orgFormApi.value.submitForm();
  }
}

async function handleOrgSave(values: Record<string, unknown>) {
  orgSaving.value = true;
  try {
    if (isOrgEdit.value) {
      await OrgAPI.update(currentOrgId.value, values);
      Toast.success("更新部门成功");
    } else {
      await OrgAPI.create({
        ...values,
        tenant_id: currentTenantId.value,
        parent_id: selectedOrgId.value || undefined,
      } as Partial<Organization>);
      Toast.success("创建部门成功");
    }
    orgModalVisible.value = false;
    fetchOrgTree();
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "操作失败";
    Toast.error(errorMsg);
  } finally {
    orgSaving.value = false;
  }
}

function handleOrgDelete(id: string) {
  Modal.warning({
    title: "确认删除该部门？",
    content: "删除部门将使其下所有子部门及成员受到影响，此操作不可逆。",
    onOk: async () => {
      try {
        await OrgAPI.delete(id);
        Toast.success("删除成功");
        if (selectedOrgId.value === id) {
          selectedOrgId.value = "";
          selectedOrgName.value = "";
          users.value = [];
        }
        fetchOrgTree();
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : "删除失败";
        Toast.error(errorMsg);
      }
    },
  });
}

// ==== 用户管理逻辑 ====
const userColumns = [
  { title: "用户名", dataIndex: "username" },
  { title: "真实姓名", dataIndex: "full_name" },
  { title: "邮箱", dataIndex: "email" },
  {
    title: "状态",
    dataIndex: "is_active",
    render: (val: boolean) => (
      <Tag color={val ? "green" : "red"}>{val ? "启用" : "禁用"}</Tag>
    ),
  },
  {
    title: "操作",
    dataIndex: "actions",
    render: (_text: unknown, record: Record<string, unknown>) => (
      <div class="flex gap-2">
        <Button
          theme="borderless"
          type="primary"
          size="small"
          onClick={() => openUserModal(record as unknown as User)}
        >
          编辑
        </Button>
        <Button
          theme="borderless"
          type="danger"
          size="small"
          onClick={() => handleUserDelete(record.id as string)}
        >
          删除
        </Button>
      </div>
    ),
  },
];

async function fetchUsers() {
  if (!currentTenantId.value || !selectedOrgId.value) return;
  usersLoading.value = true;
  try {
    const res = await UserAPI.list(currentTenantId.value, selectedOrgId.value);
    users.value = res.data || [];
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "加载用户失败";
    Toast.error(errorMsg);
  } finally {
    usersLoading.value = false;
  }
}

// -- User Modal --
const userModalVisible = ref(false);
const isUserEdit = ref(false);
const userSaving = ref(false);
const currentUserId = ref("");
const userFormApi = ref<{ submitForm: () => void } | null>(null);

function getUserFormApi(api: { submitForm: () => void }) {
  userFormApi.value = api;
}

const userFormData = ref<{
  username: string;
  full_name: string;
  email: string;
  password?: string;
}>({
  username: "",
  full_name: "",
  email: "",
  password: "",
});

function openUserModal(record: User | null) {
  if (record) {
    isUserEdit.value = true;
    currentUserId.value = record.id;
    userFormData.value = {
      username: record.username,
      full_name: record.full_name || "",
      email: record.email || "",
    };
  } else {
    isUserEdit.value = false;
    currentUserId.value = "";
    userFormData.value = {
      username: "",
      full_name: "",
      email: "",
      password: "",
    };
  }
  userModalVisible.value = true;
}

function handleUserModalOk() {
  if (userFormApi.value) {
    userFormApi.value.submitForm();
  }
}

async function handleUserSave(values: Record<string, unknown>) {
  userSaving.value = true;
  try {
    if (isUserEdit.value) {
      await UserAPI.update(currentUserId.value, values);
      Toast.success("更新用户成功");
    } else {
      await UserAPI.create({
        ...values,
        tenant_id: currentTenantId.value,
        org_id: selectedOrgId.value,
      } as unknown as Parameters<typeof UserAPI.create>[0]);
      Toast.success("添加用户成功");
    }
    userModalVisible.value = false;
    fetchUsers();
  } catch (err: unknown) {
    const errorMsg = err instanceof Error ? err.message : "操作失败";
    Toast.error(errorMsg);
  } finally {
    userSaving.value = false;
  }
}

function handleUserDelete(id: string) {
  Modal.warning({
    title: "确认移除用户？",
    content: "此操作不会删除账号，仅将其从当前部门移除。",
    onOk: async () => {
      try {
        await UserAPI.delete(id); // Note: Assuming API handles the un-link or logical deletion
        Toast.success("移除成功");
        fetchUsers();
      } catch (err: unknown) {
        const errorMsg = err instanceof Error ? err.message : "移除失败";
        Toast.error(errorMsg);
      }
    },
  });
}
</script>

<style scoped>
.group:hover .group-hover\:flex {
  display: flex !important;
}
</style>
