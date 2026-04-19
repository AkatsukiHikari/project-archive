<template>
  <div class="flex flex-col" style="height: calc(100vh - 130px)">
    <!-- Page Header -->
    <AdminPageHeader title="角色管理" description="RBAC 角色配置及菜单权限分配" icon="heroicons:shield-check">
      <NButton type="primary" :disabled="!adminStore.currentTenantId" @click="openRoleModal(null)">
        <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
        新增角色
      </NButton>
    </AdminPageHeader>

    <AdminTenantBar @change="() => { selectedRoleId = ''; selectedRoleName = ''; checkedMenuIds = []; fetchRoles() }" />

    <!-- 主体 2 列 -->
    <div class="flex gap-5 flex-1 min-h-0">
      <!-- 左侧：角色列表 -->
      <div class="admin-card flex flex-col overflow-hidden" style="width: 260px; flex-shrink: 0">
        <div class="px-4 py-3 border-b shrink-0" style="border-color: var(--semi-color-border)">
          <NInput v-model:value="roleSearchText" placeholder="搜索角色…" size="small" style="width: 100%">
            <template #prefix><Icon name="heroicons:magnifying-glass" class="w-3.5 h-3.5" /></template>
          </NInput>
        </div>

        <div class="overflow-y-auto flex-1">
          <div
            v-for="role in filteredRoles"
            :key="role.id"
            class="role-item px-4 py-3 cursor-pointer border-l-2 transition-all"
            :class="selectedRoleId === role.id ? 'role-item--active' : 'border-transparent'"
            @click="handleRoleSelect(role)"
          >
            <div class="flex items-center justify-between">
              <div class="flex items-center gap-2 min-w-0">
                <div
                  class="w-6 h-6 rounded-md flex items-center justify-center shrink-0 text-[11px] font-bold"
                  :style="selectedRoleId === role.id
                    ? 'background:var(--semi-color-primary-light-default);color:var(--semi-color-primary)'
                    : 'background:var(--semi-color-fill-1);color:var(--semi-color-text-2)'"
                >
                  {{ role.name.slice(0, 1) }}
                </div>
                <span class="text-sm truncate"
                  :style="selectedRoleId === role.id
                    ? 'color:var(--semi-color-primary);font-weight:600'
                    : 'color:var(--semi-color-text-0)'">
                  {{ role.name }}
                </span>
              </div>
              <div class="flex items-center gap-1 shrink-0">
                <span v-if="role.is_system" class="text-[10px] px-1 py-0.5 rounded font-medium"
                  style="background:var(--semi-color-danger-light-default);color:var(--semi-color-danger)">
                  系统
                </span>
                <div v-if="!role.is_system" class="role-actions flex gap-0.5">
                  <NButton text size="small" aria-label="编辑" @click.stop="openRoleModal(role)">
                    <template #icon><Icon name="heroicons:pencil" class="w-3.5 h-3.5" /></template>
                  </NButton>
                  <NButton text size="small" aria-label="删除" @click.stop="handleRoleDelete(role.id)">
                    <template #icon>
                      <Icon name="heroicons:trash" class="w-3.5 h-3.5" style="color:var(--semi-color-danger)" />
                    </template>
                  </NButton>
                </div>
              </div>
            </div>
            <p class="text-[11px] mt-1 truncate" style="color:var(--semi-color-text-2);padding-left:32px">
              {{ role.description || "暂无描述" }}
            </p>
          </div>

          <div v-if="filteredRoles.length === 0"
            class="flex flex-col items-center justify-center py-12 gap-2">
            <Icon name="heroicons:inbox" class="w-8 h-8" style="color:var(--semi-color-fill-2)" />
            <span class="text-xs" style="color:var(--semi-color-text-2)">暂无角色</span>
          </div>
        </div>
      </div>

      <!-- 右侧：权限树 -->
      <div class="admin-card flex flex-col flex-1 min-w-0 overflow-hidden">
        <div class="px-5 py-3.5 border-b flex items-center justify-between shrink-0"
          style="background:var(--semi-color-fill-0);border-color:var(--semi-color-border)">
          <div>
            <div class="flex items-center gap-2">
              <span class="text-sm font-semibold" style="color:var(--semi-color-text-0)">菜单权限配置</span>
              <span v-if="selectedRoleName" class="text-xs px-2 py-0.5 rounded-full font-medium"
                style="background:var(--semi-color-primary-light-default);color:var(--semi-color-primary)">
                {{ selectedRoleName }}
              </span>
            </div>
            <p v-if="selectedRoleId" class="text-[11px] mt-0.5" style="color:var(--semi-color-text-2)">
              勾选功能模块以分配菜单访问权限
            </p>
          </div>
          <div v-if="selectedRoleId && !isSelectedRoleSystem" class="flex gap-2">
            <NButton size="small" @click="resetPermissions">重置</NButton>
            <NButton type="primary" size="small" :loading="savingPermissions" @click="savePermissions">
              <template #icon><Icon name="heroicons:check" class="w-4 h-4" /></template>
              保存
            </NButton>
          </div>
        </div>

        <div class="flex-1 overflow-y-auto p-5 relative">
          <div v-if="!selectedRoleId"
            class="absolute inset-0 flex flex-col items-center justify-center gap-2">
            <Icon name="heroicons:cursor-arrow-rays" class="w-10 h-10" style="color:var(--semi-color-fill-2)" />
            <span class="text-sm" style="color:var(--semi-color-text-2)">请在左侧选择一个角色</span>
          </div>
          <NTree
            v-else
            :data="menuTreeData"
            checkable
            default-expand-all
            :checked-keys="checkedMenuIds"
            :disabled="isSelectedRoleSystem"
            key-field="key"
            label-field="label"
            children-field="children"
            @update:checked-keys="checkedMenuIds = $event as string[]"
          />
        </div>
      </div>
    </div>

    <!-- 新增/编辑角色弹窗 -->
    <CrudModal
      v-model:visible="roleModalVisible"
      :title="isRoleEdit ? '编辑角色' : '新增角色'"
      :loading="roleSaving"
      :width="420"
      @confirm="submitRoleForm"
    >
      <NForm ref="roleFormRef" :model="roleFormData" :rules="roleFormRules" label-placement="left" :label-width="80" class="mt-1">
        <NFormItem path="name" label="角色名称">
          <NInput v-model:value="roleFormData.name" placeholder="例如：部门管理员" />
        </NFormItem>
        <NFormItem path="code" label="角色标识">
          <NInput v-model:value="roleFormData.code" :disabled="isRoleEdit" placeholder="例如：dept_admin（不可修改）" />
        </NFormItem>
        <NFormItem path="description" label="描述">
          <NInput v-model:value="roleFormData.description" placeholder="角色描述" />
        </NFormItem>
      </NForm>
    </CrudModal>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, onMounted, reactive } from "vue";
import { NButton, NInput, NTree, NForm, NFormItem, useMessage, useDialog } from "naive-ui";
import type { FormInst, TreeOption } from "naive-ui";
import { RoleAPI, MenuAPI, type Role, type MenuTree } from "@/api/iam";
import { useAdminStore } from "@/stores/admin";
import AdminPageHeader from "@/components/admin/PageHeader.vue";
import AdminTenantBar from "@/components/admin/TenantBar.vue";
import CrudModal from "@/components/ui/CrudModal.vue";

definePageMeta({ layout: "admin", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();
const adminStore = useAdminStore();

const roles = ref<Role[]>([]);
const roleSearchText = ref("");
const selectedRoleId = ref("");
const selectedRoleName = ref("");
const isSelectedRoleSystem = ref(false);

const menuTreeData = ref<TreeOption[]>([]);
const checkedMenuIds = ref<string[]>([]);
const originalCheckedIds = ref<string[]>([]);
const savingPermissions = ref(false);

const filteredRoles = computed(() => {
  if (!roleSearchText.value) return roles.value;
  const q = roleSearchText.value.toLowerCase();
  return roles.value.filter((r) => r.name.toLowerCase().includes(q) || r.code.toLowerCase().includes(q));
});

onMounted(() => {
  if (adminStore.currentTenantId) fetchRoles();
  fetchMenuTree();
});

watch(() => adminStore.currentTenantId, (id) => {
  if (id) { selectedRoleId.value = ""; selectedRoleName.value = ""; checkedMenuIds.value = []; fetchRoles(); }
});

async function fetchRoles() {
  if (!adminStore.currentTenantId) return;
  try {
    const res = (await RoleAPI.list(adminStore.currentTenantId)) as any;
    roles.value = res.data || [];
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "加载角色失败");
  }
}

function handleRoleSelect(role: Role) {
  selectedRoleId.value = role.id;
  selectedRoleName.value = role.name;
  isSelectedRoleSystem.value = role.is_system;
  const ids = role.menus?.map((m) => m.id) || [];
  checkedMenuIds.value = ids;
  originalCheckedIds.value = [...ids];
}

// ── 角色 modal ───────────────────────────────────────────────────
const roleModalVisible = ref(false);
const isRoleEdit = ref(false);
const roleSaving = ref(false);
const roleFormRef = ref<FormInst | null>(null);

const roleFormData = reactive({ name: "", code: "", description: "" });
const roleFormRules = {
  name: [{ required: true, message: "请输入角色名称", trigger: "blur" }],
  code: [{ required: true, message: "请输入唯一英文标识", trigger: "blur" }],
};

function submitRoleForm() {
  roleFormRef.value?.validate((errors) => { if (!errors) handleRoleSave(); });
}

function openRoleModal(role: Role | null) {
  if (role) {
    isRoleEdit.value = true;
    Object.assign(roleFormData, { name: role.name, code: role.code, description: role.description || "" });
  } else {
    isRoleEdit.value = false;
    Object.assign(roleFormData, { name: "", code: "", description: "" });
  }
  roleModalVisible.value = true;
}

async function handleRoleSave() {
  roleSaving.value = true;
  try {
    if (isRoleEdit.value) {
      await RoleAPI.update(selectedRoleId.value, { ...roleFormData });
      message.success("更新成功");
    } else {
      await RoleAPI.create({ ...roleFormData, tenant_id: adminStore.currentTenantId } as any);
      message.success("创建成功");
    }
    roleModalVisible.value = false;
    fetchRoles();
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "保存失败");
  } finally {
    roleSaving.value = false;
  }
}

function handleRoleDelete(id: string) {
  dialog.warning({
    title: "确认删除该角色？",
    content: "删除后不可恢复，已绑定该角色的用户将失去对应权限。",
    positiveText: "确认删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await RoleAPI.delete(id);
        message.success("删除成功");
        if (selectedRoleId.value === id) { selectedRoleId.value = ""; selectedRoleName.value = ""; }
        fetchRoles();
      } catch (err: unknown) {
        message.error(err instanceof Error ? err.message : "删除失败");
      }
    },
  });
}

// ── 菜单树 ────────────────────────────────────────────────────────
function transformToTreeOptions(nodes: MenuTree[]): TreeOption[] {
  return nodes.map((node) => ({
    key: node.id,
    label: node.name,
    children: node.children?.length ? transformToTreeOptions(node.children) : undefined,
  }));
}

async function fetchMenuTree() {
  try {
    const res = (await MenuAPI.tree()) as any;
    menuTreeData.value = transformToTreeOptions(res.data || []);
  } catch {
    message.error("加载权限配置失败");
  }
}

function resetPermissions() {
  checkedMenuIds.value = [...originalCheckedIds.value];
}

async function savePermissions() {
  if (!selectedRoleId.value) return;
  savingPermissions.value = true;
  try {
    await RoleAPI.update(selectedRoleId.value, { menu_ids: checkedMenuIds.value });
    message.success("权限保存成功");
    originalCheckedIds.value = [...checkedMenuIds.value];
    fetchRoles();
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "权限保存失败");
  } finally {
    savingPermissions.value = false;
  }
}
</script>

<style scoped>
.admin-card {
  background: var(--semi-color-bg-0);
  border: 1px solid var(--semi-color-border);
  border-radius: 12px;
  overflow: hidden;
}
.role-item { border-bottom: 1px solid var(--semi-color-border); }
.role-item:hover { background: var(--semi-color-fill-0); }
.role-item--active {
  background: var(--semi-color-primary-light-default);
  border-left-color: var(--semi-color-primary) !important;
}
.role-actions { opacity: 0; transition: opacity 0.15s; }
.role-item:hover .role-actions { opacity: 1; }
</style>
