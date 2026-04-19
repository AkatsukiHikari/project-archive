<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader title="用户管理" description="管理所有租户用户账号，分配部门与角色" icon="heroicons:user-group" />
    <AdminTenantBar @change="onTenantChange" />

    <ProTable :columns="columns" :data="filteredUsers" :loading="loading" empty-content="暂无用户数据">
      <template #toolbar-left>
        <NInput v-model:value="searchText" placeholder="搜索用户名 / 姓名 / 邮箱…" style="width: 260px" clearable>
          <template #prefix><Icon name="heroicons:magnifying-glass" class="w-4 h-4" /></template>
        </NInput>
        <NSelect v-model:value="filterStatus" :options="statusOptions" style="width: 110px" placeholder="状态" />
      </template>
      <template #toolbar-right>
        <NButton type="primary" :disabled="!adminStore.currentTenantId" @click="openModal(null)">
          <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
          新增用户
        </NButton>
      </template>
    </ProTable>

    <CrudModal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑用户' : '新增用户'"
      :loading="saving"
      :width="540"
      @confirm="submitForm"
    >
      <NForm ref="formRef" :model="formData" :rules="formRules" label-placement="left" :label-width="80">
        <NFormItem path="username" label="用户名">
          <NInput v-model:value="formData.username" :disabled="isEdit" placeholder="登录用户名（创建后不可修改）" />
        </NFormItem>
        <NFormItem path="full_name" label="姓名">
          <NInput v-model:value="formData.full_name" placeholder="真实姓名" />
        </NFormItem>
        <NFormItem path="email" label="邮箱">
          <NInput v-model:value="formData.email" placeholder="登录邮箱" />
        </NFormItem>
        <NFormItem path="phone" label="手机号">
          <NInput v-model:value="formData.phone" placeholder="可选" />
        </NFormItem>
        <NFormItem path="org_id" label="所属部门">
          <NSelect v-model:value="formData.org_id" :options="orgOptions" placeholder="未分配部门" clearable />
        </NFormItem>
        <NFormItem path="role_ids" label="角色">
          <NSelect v-model:value="formData.role_ids" :options="roleOptions" placeholder="分配角色" multiple clearable />
        </NFormItem>
        <NFormItem v-if="!isEdit" path="password" label="初始密码">
          <NInput v-model:value="formData.password" type="password" placeholder="初始登录密码" show-password-on="click" />
        </NFormItem>
      </NForm>
    </CrudModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, watch, onMounted, reactive } from "vue";
import { NButton, NInput, NSelect, NForm, NFormItem, NTag, useMessage, useDialog } from "naive-ui";
import type { FormInst } from "naive-ui";
import { UserAPI, OrgAPI, RoleAPI, type User, type Role, type OrganizationTree, type UserUpdatePayload } from "@/api/iam";
import { useAdminStore } from "@/stores/admin";
import AdminPageHeader from "@/components/admin/PageHeader.vue";
import AdminTenantBar from "@/components/admin/TenantBar.vue";
import ProTable from "@/components/ui/ProTable.vue";
import CrudModal from "@/components/ui/CrudModal.vue";

definePageMeta({ layout: "admin", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();
const adminStore = useAdminStore();

// ── 数据 ──────────────────────────────────────────────────────────
const users = ref<User[]>([]);
const loading = ref(false);
const orgList = ref<{ id: string; name: string }[]>([]);
const roleList = ref<Role[]>([]);
const searchText = ref("");
const filterStatus = ref<string | null>(null);

const statusOptions = [
  { label: "全部", value: "" },
  { label: "启用", value: "active" },
  { label: "禁用", value: "inactive" },
];

const orgOptions = computed(() => orgList.value.map((o) => ({ label: o.name, value: o.id })));
const roleOptions = computed(() => roleList.value.map((r) => ({ label: r.name, value: r.id })));

const filteredUsers = computed(() => {
  let list = users.value;
  if (searchText.value) {
    const q = searchText.value.toLowerCase();
    list = list.filter(
      (u) =>
        u.username.toLowerCase().includes(q) ||
        (u.full_name ?? "").toLowerCase().includes(q) ||
        (u.email ?? "").toLowerCase().includes(q),
    );
  }
  if (filterStatus.value === "active") list = list.filter((u) => u.is_active);
  if (filterStatus.value === "inactive") list = list.filter((u) => !u.is_active);
  return list;
});

function onTenantChange() { fetchUsers(); fetchFlatOrgs(); fetchRoles(); }

onMounted(() => {
  if (adminStore.currentTenantId) onTenantChange();
});

watch(() => adminStore.currentTenantId, (id) => { if (id) onTenantChange(); });

async function fetchUsers() {
  if (!adminStore.currentTenantId) return;
  loading.value = true;
  try {
    const res = (await UserAPI.list(adminStore.currentTenantId)) as any;
    users.value = res.data ?? [];
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "加载用户失败");
  } finally {
    loading.value = false;
  }
}

function flattenOrgs(nodes: OrganizationTree[]): { id: string; name: string }[] {
  return nodes.flatMap((n) => [{ id: n.id, name: n.name }, ...flattenOrgs(n.children ?? [])]);
}

async function fetchFlatOrgs() {
  if (!adminStore.currentTenantId) return;
  try {
    const res = (await OrgAPI.tree(adminStore.currentTenantId)) as any;
    orgList.value = flattenOrgs(res.data ?? []);
  } catch { /* 静默失败 */ }
}

async function fetchRoles() {
  if (!adminStore.currentTenantId) return;
  try {
    const res = (await RoleAPI.list(adminStore.currentTenantId)) as any;
    roleList.value = res.data ?? [];
  } catch { /* 静默失败 */ }
}

// ── 表格列 ────────────────────────────────────────────────────────
const columns = [
  {
    title: "用户", key: "username",
    render: (row: User) => {
      const initials = (row.full_name || row.username).slice(0, 1).toUpperCase();
      return (
        <div class="flex items-center gap-2.5 py-1">
          <div class="w-8 h-8 rounded-full flex items-center justify-center text-sm font-semibold shrink-0"
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
    title: "所属部门", key: "org_id", width: 160,
    render: (row: User) => {
      const org = orgList.value.find((o) => o.id === row.org_id);
      return org ? <NTag size="small">{org.name}</NTag> : <span style="color:var(--semi-color-text-3)">—</span>;
    },
  },
  {
    title: "角色", key: "roles", width: 180,
    render: (row: User) => {
      if (!row.roles?.length) return <span style="color:var(--semi-color-text-3)">—</span>;
      return (
        <div class="flex flex-wrap gap-1 py-0.5">
          {row.roles.slice(0, 2).map((r) => <NTag key={r.id} type="info" size="small">{r.name}</NTag>)}
          {row.roles.length > 2 && <NTag size="small">+{row.roles.length - 2}</NTag>}
        </div>
      );
    },
  },
  {
    title: "状态", key: "is_active", width: 80,
    render: (row: User) => row.is_active
      ? <NTag type="success" size="small">启用</NTag>
      : <NTag type="error" size="small">禁用</NTag>,
  },
  {
    title: "操作", key: "_actions", width: 150,
    render: (row: User) => (
      <div class="flex gap-1">
        <NButton text type="primary" size="small" onClick={() => openModal(row)}>编辑</NButton>
        <NButton text size="small" onClick={() => toggleStatus(row)}>{row.is_active ? "禁用" : "启用"}</NButton>
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
  username: "", full_name: "", email: "", phone: "",
  org_id: null as string | null,
  role_ids: [] as string[],
  password: "",
});

const formRules = {
  username: [{ required: true, message: "请输入登录用户名", trigger: "blur" }],
  full_name: [{ required: true, message: "请输入姓名", trigger: "blur" }],
  email: [{ required: true, message: "请输入邮箱", trigger: "blur" }],
  password: [{ required: true, message: "请输入初始密码", trigger: "blur" }],
};

function submitForm() {
  formRef.value?.validate((errors) => { if (!errors) handleSave(); });
}

function openModal(record: User | null) {
  if (record) {
    isEdit.value = true;
    currentId.value = record.id;
    Object.assign(formData, {
      username: record.username, full_name: record.full_name ?? "", email: record.email,
      phone: (record as any).phone ?? "", org_id: record.org_id ?? null,
      role_ids: record.roles?.map((r) => r.id) ?? [], password: "",
    });
  } else {
    isEdit.value = false;
    currentId.value = "";
    Object.assign(formData, { username: "", full_name: "", email: "", phone: "", org_id: null, role_ids: [], password: "" });
  }
  modalVisible.value = true;
}

async function handleSave() {
  saving.value = true;
  try {
    if (isEdit.value) {
      await UserAPI.update(currentId.value, { ...formData } as UserUpdatePayload);
      message.success("更新成功");
    } else {
      await UserAPI.create({ ...formData, tenant_id: adminStore.currentTenantId } as any);
      message.success("用户创建成功");
    }
    modalVisible.value = false;
    fetchUsers();
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "保存失败");
  } finally {
    saving.value = false;
  }
}

async function toggleStatus(u: User) {
  try {
    await UserAPI.update(u.id, { is_active: !u.is_active });
    message.success(u.is_active ? "已禁用" : "已启用");
    fetchUsers();
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "操作失败");
  }
}

function handleDelete(id: string) {
  dialog.warning({
    title: "确认删除用户？",
    content: "此操作不可逆，删除后用户将无法登录。",
    positiveText: "确认删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await UserAPI.delete(id);
        message.success("删除成功");
        fetchUsers();
      } catch (err: unknown) {
        message.error(err instanceof Error ? err.message : "删除失败");
      }
    },
  });
}
</script>
