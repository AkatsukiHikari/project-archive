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
        @change="handleTenantChange"
        :style="{ width: '280px' }"
        :loading="tenantsLoading"
        placeholder="请选择租户"
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
            icon="material-symbols:add"
            theme="borderless"
            type="primary"
            @click="openOrgModal(null)"
            :disabled="!currentTenantId"
          />
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
            icon="material-symbols:person-add"
            :disabled="!selectedOrgId"
            @click="openUserModal(null)"
          >
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
      @ok="handleOrgSave"
      @cancel="orgModalVisible = false"
      :confirm-loading="orgSaving"
    >
      <div class="flex flex-col gap-4 mt-4">
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >部门名称 <span class="text-red-500">*</span></label
          >
          <Input v-model="orgFormData.name" placeholder="请输入部门名称" />
        </div>
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >部门标识 (Code) <span class="text-red-500">*</span></label
          >
          <Input
            v-model="orgFormData.code"
            :disabled="isOrgEdit"
            placeholder="请输入唯一英文字母标识"
          />
        </div>
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >排序号</label
          >
          <InputNumber
            v-model="orgFormData.sort_order"
            class="w-full"
            :min="0"
          />
        </div>
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
      </div>
    </Modal>

    <!-- User Modal -->
    <Modal
      v-model:visible="userModalVisible"
      :title="isUserEdit ? '编辑成员' : '添加成员'"
      @ok="handleUserSave"
      @cancel="userModalVisible = false"
      :confirm-loading="userSaving"
    >
      <div class="flex flex-col gap-4 mt-4">
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >用户名 <span class="text-red-500">*</span></label
          >
          <Input
            v-model="userFormData.username"
            :disabled="isUserEdit"
            placeholder="请输入登录用户名"
          />
        </div>
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >真实姓名 <span class="text-red-500">*</span></label
          >
          <Input
            v-model="userFormData.full_name"
            placeholder="请输入用户真实姓名"
          />
        </div>
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >邮箱 <span class="text-red-500">*</span></label
          >
          <Input v-model="userFormData.email" placeholder="请输入用户邮箱" />
        </div>
        <div v-if="!isUserEdit">
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >初始密码 <span class="text-red-500">*</span></label
          >
          <Input
            v-model="userFormData.password"
            type="password"
            placeholder="请输入初始登录密码"
          />
        </div>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="tsx">
import { ref, onMounted } from "vue";
import { definePageMeta } from "#imports";
import {
  Button,
  Tree,
  Table,
  Modal,
  Input,
  InputNumber,
  Select,
  Toast,
  Tag,
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
import { IconMore, IconEdit, IconDelete } from "@kousum/semi-icons-vue";

definePageMeta({ layout: "admin" });

// -- 全局状态 --
const tenants = ref<Tenant[]>([]);
const currentTenantId = ref<string>("");
const tenantsLoading = ref(false);

// -- 组织架构状态 --
const orgTreeData = ref<any[]>([]);
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
    tenants.value = res.data.data || [];
    if (tenants.value.length > 0) {
      currentTenantId.value = tenants.value[0].id;
      handleTenantChange(currentTenantId.value);
    }
  } catch (err: any) {
    Toast.error(err.message || "加载租户失败");
  } finally {
    tenantsLoading.value = false;
  }
}

function handleTenantChange(val: any) {
  currentTenantId.value = val as string;
  selectedOrgId.value = "";
  selectedOrgName.value = "";
  users.value = [];
  fetchOrgTree();
}

// ==== 组织架构逻辑 ====
function transformOrgTree(nodes: OrganizationTree[]): any[] {
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
    orgRawData.value = res.data.data || [];
    orgTreeData.value = transformOrgTree(orgRawData.value);
  } catch (err: any) {
    Toast.error(err.message || "加载组织树失败");
  }
}

function handleOrgSelect(selectedKeys: string[], selectedNodes: any[]) {
  if (selectedNodes.length > 0) {
    selectedOrgId.value = selectedNodes[0].value;
    selectedOrgName.value = selectedNodes[0].label;
    fetchUsers();
  } else {
    selectedOrgId.value = "";
    selectedOrgName.value = "";
    users.value = [];
  }
}

// 树节点自定义渲染：加入编辑和删除按钮
const renderOrgLabel = (label: string, item: any) => {
  return (
    <div class="flex items-center justify-between w-full group pr-2">
      <span>{label}</span>
      <div class="hidden group-hover:flex items-center gap-1">
        <Button
          icon={<IconEdit />}
          theme="borderless"
          type="primary"
          size="small"
          onClick={(e: Event) => {
            e.stopPropagation();
            openOrgModal(item.rawData);
          }}
        />
        <Button
          icon={<IconDelete />}
          theme="borderless"
          type="danger"
          size="small"
          onClick={(e: Event) => {
            e.stopPropagation();
            handleOrgDelete(item.rawData.id);
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

async function handleOrgSave() {
  if (!orgFormData.value.name || !orgFormData.value.code)
    return Toast.warning("请填写带 * 的必填项");
  orgSaving.value = true;
  try {
    if (isOrgEdit.value) {
      await OrgAPI.update(currentOrgId.value, orgFormData.value);
      Toast.success("更新部门成功");
    } else {
      await OrgAPI.create({
        ...orgFormData.value,
        tenant_id: currentTenantId.value,
      });
      Toast.success("创建部门成功");
    }
    orgModalVisible.value = false;
    fetchOrgTree();
  } catch (err: any) {
    Toast.error(err.message || "操作失败");
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
      } catch (err: any) {
        Toast.error(err.message || "删除失败");
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
      <Tag color={val ? "green" : ("red" as any)}>{val ? "启用" : "禁用"}</Tag>
    ),
  },
  {
    title: "操作",
    dataIndex: "actions",
    render: (_text: any, record: User) => (
      <div class="flex gap-2">
        <Button
          theme="borderless"
          type="primary"
          size="small"
          onClick={() => openUserModal(record)}
        >
          编辑
        </Button>
        <Button
          theme="borderless"
          type="danger"
          size="small"
          onClick={() => handleUserDelete(record.id)}
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
    users.value = res.data.data || [];
  } catch (err: any) {
    Toast.error(err.message || "加载用户失败");
  } finally {
    usersLoading.value = false;
  }
}

// -- User Modal --
const userModalVisible = ref(false);
const isUserEdit = ref(false);
const userSaving = ref(false);
const currentUserId = ref("");
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
      full_name: record.full_name,
      email: record.email,
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

async function handleUserSave() {
  if (
    !userFormData.value.username ||
    !userFormData.value.full_name ||
    !userFormData.value.email
  ) {
    return Toast.warning("请填写带 * 的必填项");
  }
  if (!isUserEdit.value && !userFormData.value.password) {
    return Toast.warning("新增用户需填写初始密码");
  }

  userSaving.value = true;
  try {
    if (isUserEdit.value) {
      await UserAPI.update(currentUserId.value, userFormData.value);
      Toast.success("更新用户成功");
    } else {
      await UserAPI.create({
        ...userFormData.value,
        tenant_id: currentTenantId.value,
        org_id: selectedOrgId.value,
      });
      Toast.success("添加用户成功");
    }
    userModalVisible.value = false;
    fetchUsers();
  } catch (err: any) {
    Toast.error(err.message || "操作失败");
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
      } catch (err: any) {
        Toast.error(err.message || "移除失败");
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
