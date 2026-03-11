<template>
  <div class="flex flex-col gap-4">
    <!-- 顶部租户选择 -->
    <div
      class="bg-[var(--semi-color-bg-0)] rounded-xl border border-[var(--semi-color-border)] shadow-sm p-4 flex items-center justify-between"
    >
      <div class="flex items-center gap-4">
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
      <div class="flex gap-2">
        <Input prefix="search" placeholder="搜索用户..." class="w-64" />
        <Button
          theme="solid"
          type="primary"
          icon="material-symbols:person-add"
          :disabled="!currentTenantId"
          @click="openUserModal(null)"
        >
          新增用户
        </Button>
      </div>
    </div>

    <div
      class="bg-[var(--semi-color-bg-0)] rounded-xl border border-[var(--semi-color-border)] shadow-sm p-6 min-h-[500px]"
    >
      <Table
        :columns="columns"
        :data-source="users"
        :loading="loading"
        empty-text="暂无用户数据"
      />
    </div>

    <!-- 用户弹窗 -->
    <Modal
      v-model:visible="userModalVisible"
      :title="isEdit ? '编辑用户' : '新增用户'"
      @ok="handleSave"
      @cancel="userModalVisible = false"
      :confirm-loading="saving"
    >
      <div class="flex flex-col gap-4 mt-4">
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >用户名 <span class="text-red-500">*</span></label
          >
          <Input
            v-model="formData.username"
            :disabled="isEdit"
            placeholder="请输入登录用户名"
          />
        </div>
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >真实姓名 <span class="text-red-500">*</span></label
          >
          <Input
            v-model="formData.full_name"
            placeholder="请输入用户真实姓名"
          />
        </div>
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >邮箱 <span class="text-red-500">*</span></label
          >
          <Input v-model="formData.email" placeholder="请输入用户邮箱" />
        </div>
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >所属部门</label
          >
          <!-- 这里使用 Select 下拉列表渲染部门，如果没有就不选 -->
          <Select
            v-model="formData.org_id"
            class="w-full"
            placeholder="未分配部门"
          >
            <Select.Option
              v-for="org in orgList"
              :key="org.id"
              :value="org.id"
              >{{ org.name }}</Select.Option
            >
          </Select>
        </div>
        <div v-if="!isEdit">
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >初始密码 <span class="text-red-500">*</span></label
          >
          <Input
            v-model="formData.password"
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
  Table,
  Input,
  Select,
  Modal,
  Toast,
  Tag,
} from "@kousum/semi-ui-vue";
import {
  TenantAPI,
  UserAPI,
  OrgAPI,
  type Tenant,
  type User,
  type OrganizationTree,
} from "@/api/iam";

definePageMeta({ layout: "admin" });

const tenants = ref<Tenant[]>([]);
const currentTenantId = ref<string>("");
const tenantsLoading = ref(false);

const users = ref<User[]>([]);
const loading = ref(false);
const orgList = ref<any[]>([]);

const columns = [
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
    title: "创建时间",
    dataIndex: "create_time",
    render: (text: string) => new Date(text).toLocaleString(),
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
          onClick={() => handleDelete(record.id)}
        >
          删除
        </Button>
      </div>
    ),
  },
];

onMounted(async () => {
  await fetchTenants();
});

async function fetchTenants() {
  tenantsLoading.value = true;
  try {
    const res = (await TenantAPI.list()) as any;
    tenants.value = res.data || [];
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
  fetchUsers();
  fetchFlatOrgs();
}

async function fetchUsers() {
  if (!currentTenantId.value) return;
  loading.value = true;
  try {
    const res = (await UserAPI.list(currentTenantId.value)) as any;
    users.value = res.data || [];
  } catch (err: any) {
    Toast.error(err.message || "加载用户失败");
  } finally {
    loading.value = false;
  }
}

// 扁平化组织树以下拉列表展示
function flattenOrgs(nodes: OrganizationTree[]): any[] {
  let list: any[] = [];
  for (const node of nodes) {
    list.push({ id: node.id, name: node.name });
    if (node.children) {
      list = list.concat(flattenOrgs(node.children));
    }
  }
  return list;
}

async function fetchFlatOrgs() {
  if (!currentTenantId.value) return;
  try {
    const res = await OrgAPI.tree(currentTenantId.value);
    orgList.value = flattenOrgs((res as any).data || []);
  } catch (err: any) {
    // 忽略加载部门的错误
  }
}

// -- Modal Logic --
const userModalVisible = ref(false);
const isEdit = ref(false);
const saving = ref(false);
const currentId = ref("");
const formData = ref<{
  username: string;
  full_name: string;
  email: string;
  password?: string;
  org_id?: string;
}>({
  username: "",
  full_name: "",
  email: "",
  password: "",
  org_id: undefined,
});

function openUserModal(record: User | null) {
  if (record) {
    isEdit.value = true;
    currentId.value = record.id;
    formData.value = {
      username: record.username,
      full_name: record.full_name,
      email: record.email,
      org_id: record.org_id,
    };
  } else {
    isEdit.value = false;
    currentId.value = "";
    formData.value = {
      username: "",
      full_name: "",
      email: "",
      password: "",
      org_id: undefined,
    };
  }
  userModalVisible.value = true;
}

async function handleSave() {
  if (
    !formData.value.username ||
    !formData.value.full_name ||
    !formData.value.email
  ) {
    return Toast.warning("请填写带 * 的必填项");
  }
  if (!isEdit.value && !formData.value.password) {
    return Toast.warning("新增用户需填写初始密码");
  }

  saving.value = true;
  try {
    if (isEdit.value) {
      await UserAPI.update(currentId.value, formData.value);
      Toast.success("更新用户成功");
    } else {
      await UserAPI.create({
        ...formData.value,
        tenant_id: currentTenantId.value,
      });
      Toast.success("添加用户成功");
    }
    userModalVisible.value = false;
    fetchUsers();
  } catch (err: any) {
    Toast.error(err.message || "保存失败");
  } finally {
    saving.value = false;
  }
}

function handleDelete(id: string) {
  Modal.warning({
    title: "确认删除用户？",
    content: "此操作不可逆。",
    onOk: async () => {
      try {
        await UserAPI.delete(id);
        Toast.success("删除成功");
        fetchUsers();
      } catch (err: any) {
        Toast.error(err.message || "删除失败");
      }
    },
  });
}
</script>
