<template>
  <div class="flex flex-col gap-4" style="height: calc(100vh - 130px)">
    <AdminPageHeader title="组织架构" description="部门层级管理与人员归属配置" icon="heroicons:building-office-2" />
    <AdminTenantBar @change="onTenantChange" />

    <div class="flex gap-4 flex-1 min-h-0">
      <!-- 左：部门树 -->
      <div class="pro-card flex flex-col overflow-hidden" style="width: 280px; flex-shrink: 0">
        <div class="flex items-center gap-2 px-4 py-3 border-b shrink-0" style="border-color:var(--semi-color-border)">
          <NInput v-model:value="orgSearch" placeholder="搜索部门…" size="small" style="flex:1" clearable>
            <template #prefix><Icon name="heroicons:magnifying-glass" class="w-3.5 h-3.5" /></template>
          </NInput>
          <NButton text size="small" :disabled="!adminStore.currentTenantId" @click="openOrgModal(null)">
            <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
          </NButton>
        </div>
        <div class="flex-1 overflow-y-auto p-3">
          <NTree
            v-if="orgTreeData.length"
            :data="orgTreeData"
            default-expand-all
            :pattern="orgSearch"
            :selected-keys="selectedOrgId ? [selectedOrgId] : []"
            key-field="key"
            label-field="label"
            children-field="children"
            :render-label="renderOrgLabel"
            @update:selected-keys="handleOrgSelect"
          />
          <div v-else class="flex flex-col items-center justify-center py-12 gap-2">
            <Icon name="heroicons:building-office" class="w-8 h-8" style="color:var(--semi-color-fill-2)" />
            <span class="text-xs" style="color:var(--semi-color-text-2)">暂无部门</span>
          </div>
        </div>
      </div>

      <!-- 右：成员 ProTable -->
      <div class="flex flex-col flex-1 min-w-0">
        <ProTable :columns="userColumns" :data="users" :loading="usersLoading" empty-content="该部门暂无成员">
          <template #toolbar-left>
            <span class="text-[13px] font-semibold" style="color:var(--semi-color-text-0)">
              {{ selectedOrgName ? `部门成员 · ${selectedOrgName}` : '部门成员' }}
            </span>
          </template>
          <template #toolbar-right>
            <NButton type="primary" size="small" :disabled="!selectedOrgId" @click="openUserModal(null)">
              <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
              添加成员
            </NButton>
          </template>
        </ProTable>
        <div v-if="!selectedOrgId" class="flex flex-col items-center justify-center mt-16 gap-2">
          <Icon name="heroicons:cursor-arrow-rays" class="w-10 h-10" style="color:var(--semi-color-fill-2)" />
          <span class="text-sm" style="color:var(--semi-color-text-2)">请先在左侧选择一个部门</span>
        </div>
      </div>
    </div>

    <!-- 部门 Modal -->
    <CrudModal v-model:visible="orgModalVisible" :title="isOrgEdit ? '编辑部门' : '新增部门'" :loading="orgSaving" :width="440" @confirm="submitOrgForm">
      <NForm ref="orgFormRef" :model="orgFormData" :rules="orgFormRules" label-placement="left" :label-width="80" class="mt-1">
        <NFormItem path="name" label="部门名称">
          <NInput v-model:value="orgFormData.name" placeholder="请输入部门名称" />
        </NFormItem>
        <NFormItem path="code" label="部门标识">
          <NInput v-model:value="orgFormData.code" :disabled="isOrgEdit" placeholder="例如：finance" />
        </NFormItem>
        <NFormItem path="sort_order" label="排序号">
          <NInputNumber v-model:value="orgFormData.sort_order" :min="0" style="width:100%" />
        </NFormItem>
        <NFormItem v-if="!isOrgEdit && selectedOrgId" label="上级部门">
          <NInput :value="selectedOrgName" disabled />
        </NFormItem>
      </NForm>
    </CrudModal>

    <!-- 成员 Modal -->
    <CrudModal v-model:visible="userModalVisible" :title="isUserEdit ? '编辑成员' : '添加成员'" :loading="userSaving" :width="440" @confirm="submitUserForm">
      <NForm ref="userFormRef" :model="userFormData" :rules="userFormRules" label-placement="left" :label-width="80" class="mt-1">
        <NFormItem path="username" label="用户名">
          <NInput v-model:value="userFormData.username" :disabled="isUserEdit" placeholder="请输入登录用户名" />
        </NFormItem>
        <NFormItem path="full_name" label="姓名">
          <NInput v-model:value="userFormData.full_name" placeholder="请输入真实姓名" />
        </NFormItem>
        <NFormItem path="email" label="邮箱">
          <NInput v-model:value="userFormData.email" placeholder="请输入邮箱" />
        </NFormItem>
        <NFormItem v-if="!isUserEdit" path="password" label="初始密码">
          <NInput v-model:value="userFormData.password" type="password" placeholder="请输入初始密码" show-password-on="click" />
        </NFormItem>
      </NForm>
    </CrudModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, watch, onMounted, reactive, h } from "vue";
import {
  NButton, NInput, NInputNumber, NTree, NForm, NFormItem, NTag,
  useMessage, useDialog,
} from "naive-ui";
import type { FormInst, TreeOption } from "naive-ui";
import { PlusIcon, PencilIcon, TrashIcon } from "@heroicons/vue/24/outline";
import { OrgAPI, UserAPI, type OrganizationTree, type User, type Organization } from "@/api/iam";
import { useAdminStore } from "@/stores/admin";
import AdminPageHeader from "@/components/admin/PageHeader.vue";
import AdminTenantBar from "@/components/admin/TenantBar.vue";
import ProTable from "@/components/ui/ProTable.vue";
import CrudModal from "@/components/ui/CrudModal.vue";

definePageMeta({ layout: "admin", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();
const adminStore = useAdminStore();

const orgSearch = ref("");
const orgTreeData = ref<TreeOption[]>([]);
const selectedOrgId = ref("");
const selectedOrgName = ref("");
const users = ref<User[]>([]);
const usersLoading = ref(false);

// ── 组织树 ────────────────────────────────────────────────────────
function onTenantChange() { selectedOrgId.value = ""; selectedOrgName.value = ""; users.value = []; fetchOrgTree(); }

onMounted(() => { if (adminStore.currentTenantId) fetchOrgTree(); });
watch(() => adminStore.currentTenantId, (id) => { if (id) onTenantChange(); });

interface OrgTreeOption extends TreeOption {
  rawData: OrganizationTree;
  children: OrgTreeOption[];
}

function transformOrgTree(nodes: OrganizationTree[]): OrgTreeOption[] {
  return nodes.map((n) => ({
    key: n.id, label: n.name, rawData: n,
    children: transformOrgTree(n.children ?? []),
  }));
}

async function fetchOrgTree() {
  if (!adminStore.currentTenantId) return;
  try {
    const res = (await OrgAPI.tree(adminStore.currentTenantId)) as any;
    orgTreeData.value = transformOrgTree(res.data ?? []);
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "加载组织树失败");
  }
}

function handleOrgSelect(keys: Array<string | number>) {
  const key = String(keys[0] ?? "");
  if (!key) { selectedOrgId.value = ""; selectedOrgName.value = ""; users.value = []; return; }
  const findNode = (nodes: OrgTreeOption[]): OrgTreeOption | undefined => {
    for (const n of nodes) {
      if (n.key === key) return n;
      const found = findNode((n.children ?? []) as OrgTreeOption[]);
      if (found) return found;
    }
  };
  const node = findNode(orgTreeData.value as OrgTreeOption[]);
  if (node) { selectedOrgId.value = key; selectedOrgName.value = node.label as string; fetchUsers(); }
}

// 部门树节点自定义渲染（带操作按钮）
const renderOrgLabel = ({ option }: { option: TreeOption }) => {
  const node = option as OrgTreeOption;
  return (
    <div class="flex items-center justify-between w-full group pr-1">
      <span class="text-[13px] truncate">{node.label as string}</span>
      <div class="org-actions flex items-center gap-1 shrink-0">
        <NButton
          text size="small"
          onClick={(e: MouseEvent) => { e.stopPropagation(); selectedOrgId.value = node.rawData.id; selectedOrgName.value = node.rawData.name; openOrgModal(null); }}
        >
          {{ icon: () => h(PlusIcon, { class: "w-3.5 h-3.5" }) }}
        </NButton>
        <NButton
          text type="primary" size="small"
          onClick={(e: MouseEvent) => { e.stopPropagation(); openOrgModal(node.rawData as unknown as Organization); }}
        >
          {{ icon: () => h(PencilIcon, { class: "w-3.5 h-3.5" }) }}
        </NButton>
        <NButton
          text type="error" size="small"
          onClick={(e: MouseEvent) => { e.stopPropagation(); handleOrgDelete(node.rawData.id); }}
        >
          {{ icon: () => h(TrashIcon, { class: "w-3.5 h-3.5" }) }}
        </NButton>
      </div>
    </div>
  );
};

// ── 部门 modal ────────────────────────────────────────────────────
const orgModalVisible = ref(false);
const isOrgEdit = ref(false);
const orgSaving = ref(false);
const currentOrgId = ref("");
const orgFormRef = ref<FormInst | null>(null);
const orgFormData = reactive({ name: "", code: "", sort_order: 0 });
const orgFormRules = {
  name: [{ required: true, message: "请输入部门名称", trigger: "blur" }],
  code: [{ required: true, message: "请输入唯一英文标识", trigger: "blur" }],
};

function submitOrgForm() { orgFormRef.value?.validate((errors) => { if (!errors) handleOrgSave(); }); }

function openOrgModal(record: Organization | null) {
  if (record) {
    isOrgEdit.value = true; currentOrgId.value = record.id;
    Object.assign(orgFormData, { name: record.name, code: record.code, sort_order: record.sort_order || 0 });
  } else {
    isOrgEdit.value = false; currentOrgId.value = "";
    Object.assign(orgFormData, { name: "", code: "", sort_order: 0 });
  }
  orgModalVisible.value = true;
}

async function handleOrgSave() {
  orgSaving.value = true;
  try {
    if (isOrgEdit.value) {
      await OrgAPI.update(currentOrgId.value, { ...orgFormData });
      message.success("更新部门成功");
    } else {
      await OrgAPI.create({ ...orgFormData, tenant_id: adminStore.currentTenantId, parent_id: selectedOrgId.value || undefined } as Partial<Organization>);
      message.success("创建部门成功");
    }
    orgModalVisible.value = false;
    fetchOrgTree();
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "操作失败");
  } finally {
    orgSaving.value = false;
  }
}

function handleOrgDelete(id: string) {
  dialog.warning({
    title: "确认删除该部门？",
    content: "删除部门将影响其下所有子部门及成员，此操作不可逆。",
    positiveText: "确认删除", negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await OrgAPI.delete(id);
        message.success("删除成功");
        if (selectedOrgId.value === id) { selectedOrgId.value = ""; selectedOrgName.value = ""; users.value = []; }
        fetchOrgTree();
      } catch (err: unknown) {
        message.error(err instanceof Error ? err.message : "删除失败");
      }
    },
  });
}

// ── 成员表格列 ────────────────────────────────────────────────────
const userColumns = [
  {
    title: "用户", key: "username",
    render: (row: User) => {
      const initials = (row.full_name || row.username).slice(0, 1).toUpperCase();
      return (
        <div class="flex items-center gap-2.5 py-1">
          <div class="w-7 h-7 rounded-full flex items-center justify-center text-xs font-bold shrink-0"
            style="background:var(--semi-color-primary-light-default);color:var(--semi-color-primary)">
            {initials}
          </div>
          <div>
            <div class="text-[13px] font-medium" style="color:var(--semi-color-text-0)">{row.full_name || row.username}</div>
            <div class="text-[11px]" style="color:var(--semi-color-text-2)">@{row.username}</div>
          </div>
        </div>
      );
    },
  },
  {
    title: "邮箱", key: "email",
    render: (row: User) => <span class="text-[13px]" style="color:var(--semi-color-text-1)">{row.email}</span>,
  },
  {
    title: "状态", key: "is_active", width: 80,
    render: (row: User) => row.is_active
      ? <NTag type="success" size="small">启用</NTag>
      : <NTag type="error" size="small">禁用</NTag>,
  },
  {
    title: "操作", key: "_actions", width: 120,
    render: (row: User) => (
      <div class="flex gap-1">
        <NButton text type="primary" size="small" onClick={() => openUserModal(row)}>编辑</NButton>
        <NButton text type="error" size="small" onClick={() => handleUserDelete(row.id)}>移除</NButton>
      </div>
    ),
  },
];

async function fetchUsers() {
  if (!adminStore.currentTenantId || !selectedOrgId.value) return;
  usersLoading.value = true;
  try {
    const res = (await UserAPI.list(adminStore.currentTenantId, selectedOrgId.value)) as any;
    users.value = res.data ?? [];
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "加载用户失败");
  } finally {
    usersLoading.value = false;
  }
}

// ── 成员 modal ────────────────────────────────────────────────────
const userModalVisible = ref(false);
const isUserEdit = ref(false);
const userSaving = ref(false);
const currentUserId = ref("");
const userFormRef = ref<FormInst | null>(null);
const userFormData = reactive({ username: "", full_name: "", email: "", password: "" });
const userFormRules = {
  username: [{ required: true, message: "请输入登录用户名", trigger: "blur" }],
  full_name: [{ required: true, message: "请输入姓名", trigger: "blur" }],
  email: [{ required: true, message: "请输入邮箱", trigger: "blur" }],
  password: [{ required: true, message: "请输入初始密码", trigger: "blur" }],
};

function submitUserForm() { userFormRef.value?.validate((errors) => { if (!errors) handleUserSave(); }); }

function openUserModal(record: User | null) {
  if (record) {
    isUserEdit.value = true; currentUserId.value = record.id;
    Object.assign(userFormData, { username: record.username, full_name: record.full_name ?? "", email: record.email, password: "" });
  } else {
    isUserEdit.value = false; currentUserId.value = "";
    Object.assign(userFormData, { username: "", full_name: "", email: "", password: "" });
  }
  userModalVisible.value = true;
}

async function handleUserSave() {
  userSaving.value = true;
  try {
    if (isUserEdit.value) {
      await UserAPI.update(currentUserId.value, { ...userFormData });
      message.success("更新成功");
    } else {
      await UserAPI.create({ ...userFormData, tenant_id: adminStore.currentTenantId, org_id: selectedOrgId.value } as any);
      message.success("添加成功");
    }
    userModalVisible.value = false;
    fetchUsers();
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "操作失败");
  } finally {
    userSaving.value = false;
  }
}

function handleUserDelete(id: string) {
  dialog.warning({
    title: "确认移除该成员？",
    content: "此操作不会删除账号，仅将其从当前部门移除。",
    positiveText: "确认移除", negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await UserAPI.delete(id);
        message.success("移除成功");
        fetchUsers();
      } catch (err: unknown) {
        message.error(err instanceof Error ? err.message : "移除失败");
      }
    },
  });
}
</script>

<style scoped>
.pro-card {
  background: var(--semi-color-bg-0);
  border: 1px solid var(--semi-color-border);
  border-radius: 12px;
  overflow: hidden;
}
.org-actions { opacity: 0; transition: opacity 0.15s; }
.group:hover .org-actions { opacity: 1; }
</style>
