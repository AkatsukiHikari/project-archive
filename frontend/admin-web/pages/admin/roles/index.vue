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
    </div>

    <div
      class="flex flex-col lg:flex-row gap-6 h-[calc(100vh-210px)] min-h-[500px]"
    >
      <!-- Left: Role List -->
      <div
        class="w-full lg:w-1/3 xl:w-1/4 bg-[var(--semi-color-bg-0)] rounded-xl border border-[var(--semi-color-border)] shadow-sm flex flex-col overflow-hidden"
      >
        <div
          class="p-4 border-b border-[var(--semi-color-border)] flex justify-between items-center shrink-0"
        >
          <h2 class="font-semibold text-[var(--semi-color-text-0)]">
            角色列表
          </h2>
          <Button
            icon="material-symbols:add"
            theme="borderless"
            type="primary"
            @click="openRoleModal(null)"
            :disabled="!currentTenantId"
          />
        </div>
        <div class="p-3 border-b border-[var(--semi-color-border)] shrink-0">
          <Input
            prefix="search"
            placeholder="搜索角色..."
            style="width: 100%"
            v-model="roleSearchText"
          />
        </div>
        <div class="overflow-y-auto flex-1 custom-scrollbar">
          <ul class="divide-y divide-[var(--semi-color-border)]">
            <li
              v-for="role in filteredRoles"
              :key="role.id"
              class="p-3 cursor-pointer border-l-4 transition-colors group"
              :class="[
                selectedRoleId === role.id
                  ? 'bg-[var(--semi-color-primary-light-default)] border-[var(--semi-color-primary)]'
                  : 'hover:bg-[var(--semi-color-fill-0)] border-transparent',
              ]"
              @click="handleRoleSelect(role)"
            >
              <div class="flex justify-between items-center">
                <span
                  class="text-sm font-medium"
                  :class="
                    selectedRoleId === role.id
                      ? 'text-[var(--semi-color-primary)] font-bold'
                      : 'text-[var(--semi-color-text-0)]'
                  "
                >
                  {{ role.name }}
                </span>
                <div class="flex items-center gap-2">
                  <span
                    v-if="role.is_system"
                    class="text-[10px] bg-red-100 text-red-600 px-1.5 py-0.5 rounded font-medium"
                    >系统</span
                  >
                  <div
                    class="hidden group-hover:flex gap-1"
                    v-if="!role.is_system"
                  >
                    <Button
                      theme="borderless"
                      size="small"
                      aria-label="编辑角色"
                      @click.stop="openRoleModal(role)"
                      ><template #icon><IconEdit /></template
                    ></Button>
                    <Button
                      theme="borderless"
                      type="danger"
                      size="small"
                      aria-label="删除角色"
                      @click.stop="handleRoleDelete(role.id)"
                      ><template #icon><IconDelete /></template
                    ></Button>
                  </div>
                </div>
              </div>
              <p class="text-xs text-[var(--semi-color-text-2)] mt-1 truncate">
                {{ role.description || "无描述" }}
              </p>
            </li>
            <li
              v-if="filteredRoles.length === 0"
              class="p-4 text-center text-[var(--semi-color-text-2)]"
            >
              暂无角色数据
            </li>
          </ul>
        </div>
      </div>

      <!-- Right: Permissions Tree -->
      <div
        class="w-full lg:w-2/3 xl:w-3/4 bg-[var(--semi-color-bg-0)] rounded-xl border border-[var(--semi-color-border)] shadow-sm flex flex-col overflow-hidden"
      >
        <div
          class="p-4 border-b border-[var(--semi-color-border)] flex justify-between items-center bg-[var(--semi-color-fill-0)] rounded-t-xl shrink-0"
        >
          <div>
            <h2
              class="font-semibold text-[var(--semi-color-text-0)] flex items-center"
            >
              权限配置:
              <span class="ml-2 text-[var(--semi-color-primary)] font-bold">
                {{ selectedRoleName || "未选择角色" }}
              </span>
            </h2>
            <p
              class="text-xs text-[var(--semi-color-text-2)] mt-0.5"
              v-if="selectedRoleId"
            >
              勾选对应的功能模块与操作按钮以分配权限
            </p>
          </div>
          <div
            class="flex space-x-3"
            v-if="selectedRoleId && !isSelectedRoleSystem"
          >
            <Button @click="resetPermissions">重置</Button>
            <Button
              theme="solid"
              type="primary"
              icon="material-symbols:save"
              @click="savePermissions"
              :loading="savingPermissions"
              >保存配置</Button
            >
          </div>
        </div>
        <div class="p-6 overflow-y-auto flex-1 custom-scrollbar relative">
          <div
            v-if="!selectedRoleId"
            class="absolute inset-0 flex items-center justify-center text-[var(--semi-color-text-2)]"
          >
            请先在左侧选择一个角色
          </div>
          <Tree
            v-else
            :treeData="menuTreeData"
            multiple
            defaultExpandAll
            v-model:value="checkedMenuIds"
            :disabled="isSelectedRoleSystem"
          />
        </div>
      </div>
    </div>

    <!-- 角色弹窗 -->
    <Modal
      v-model:visible="roleModalVisible"
      :title="isRoleEdit ? '编辑角色' : '新增角色'"
      @ok="handleRoleSave"
      @cancel="roleModalVisible = false"
      :confirm-loading="roleSaving"
    >
      <div class="flex flex-col gap-4 mt-4">
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >角色名称 <span class="text-red-500">*</span></label
          >
          <Input v-model="roleFormData.name" placeholder="请输入角色名称" />
        </div>
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >角色标识 (Code) <span class="text-red-500">*</span></label
          >
          <Input
            v-model="roleFormData.code"
            :disabled="isRoleEdit"
            placeholder="请输入唯一英文字母标识"
          />
        </div>
        <div>
          <label
            class="block text-sm font-medium mb-1 text-[var(--semi-color-text-1)]"
            >描述</label
          >
          <Input
            v-model="roleFormData.description"
            placeholder="角色描述信息"
          />
        </div>
      </div>
    </Modal>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted } from "vue";
import { definePageMeta } from "#imports";
import { Button, Input, Tree, Select, Modal, Toast } from "@kousum/semi-ui-vue";
import {
  TenantAPI,
  RoleAPI,
  MenuAPI,
  type Tenant,
  type Role,
  type MenuTree,
} from "@/api/iam";
import { IconEdit, IconDelete } from "@kousum/semi-icons-vue";

definePageMeta({ layout: "admin" });

const tenants = ref<Tenant[]>([]);
const currentTenantId = ref<string>("");
const tenantsLoading = ref(false);

const roles = ref<Role[]>([]);
const roleSearchText = ref("");

const selectedRoleId = ref("");
const selectedRoleName = ref("");
const isSelectedRoleSystem = ref(false);

const menuTreeData = ref<any[]>([]);
const checkedMenuIds = ref<string[]>([]);
const originalCheckedIds = ref<string[]>([]);
const savingPermissions = ref(false);

onMounted(async () => {
  await fetchTenants();
  await fetchMenuTree();
});

// ==== Tenant Logic ====
async function fetchTenants() {
  tenantsLoading.value = true;
  try {
    const res = await TenantAPI.list();
    tenants.value = (res as any).data || [];
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
  selectedRoleId.value = "";
  selectedRoleName.value = "";
  checkedMenuIds.value = [];
  fetchRoles();
}

// ==== Roles Logic ====
async function fetchRoles() {
  if (!currentTenantId.value) return;
  try {
    const res = await RoleAPI.list(currentTenantId.value);
    roles.value = (res as any).data || [];
  } catch (err: any) {
    Toast.error(err.message || "加载角色列表失败");
  }
}

const filteredRoles = computed(() => {
  if (!roleSearchText.value) return roles.value;
  return roles.value.filter(
    (r) =>
      r.name.includes(roleSearchText.value) ||
      r.code.includes(roleSearchText.value),
  );
});

function handleRoleSelect(role: Role) {
  selectedRoleId.value = role.id;
  selectedRoleName.value = role.name;
  isSelectedRoleSystem.value = role.is_system;

  // 提取菜单 ID (需要后端返回菜单关联数据)
  const menuIds = role.menus?.map((m) => m.id) || [];
  checkedMenuIds.value = menuIds;
  originalCheckedIds.value = [...menuIds];
}

// -- Role Modal --
const roleModalVisible = ref(false);
const isRoleEdit = ref(false);
const roleSaving = ref(false);
const roleFormData = ref({ name: "", code: "", description: "" });

function openRoleModal(role: Role | null) {
  if (role) {
    isRoleEdit.value = true;
    roleFormData.value = {
      name: role.name,
      code: role.code,
      description: role.description || "",
    };
  } else {
    isRoleEdit.value = false;
    roleFormData.value = { name: "", code: "", description: "" };
  }
  roleModalVisible.value = true;
}

async function handleRoleSave() {
  if (!roleFormData.value.name || !roleFormData.value.code)
    return Toast.warning("内容不能为空");
  roleSaving.value = true;
  try {
    if (isRoleEdit.value) {
      await RoleAPI.update(selectedRoleId.value, roleFormData.value);
      Toast.success("更新成功");
    } else {
      await RoleAPI.create({
        ...roleFormData.value,
        tenant_id: currentTenantId.value,
      });
      Toast.success("创建成功");
    }
    roleModalVisible.value = false;
    fetchRoles();
  } catch (err: any) {
    Toast.error(err.message || "保存失败");
  } finally {
    roleSaving.value = false;
  }
}

function handleRoleDelete(id: string) {
  Modal.warning({
    title: "确认删除该角色？",
    content: "删除后不可恢复",
    onOk: async () => {
      try {
        await RoleAPI.delete(id);
        Toast.success("删除成功");
        if (selectedRoleId.value === id) {
          selectedRoleId.value = "";
          selectedRoleName.value = "";
        }
        fetchRoles();
      } catch (err: any) {
        Toast.error(err.message || "删除失败");
      }
    },
  });
}

// ==== Permissions Tree Logic ====
function transformMenuTree(nodes: MenuTree[]): any[] {
  return nodes.map((node) => ({
    label: node.name,
    value: node.id,
    key: node.id,
    children: node.children ? transformMenuTree(node.children) : [],
  }));
}

async function fetchMenuTree() {
  try {
    const res = await MenuAPI.tree();
    menuTreeData.value = transformMenuTree((res as any).data || []);
  } catch (err: any) {
    Toast.error("加载权限配置失败");
  }
}

function resetPermissions() {
  checkedMenuIds.value = [...originalCheckedIds.value];
}

async function savePermissions() {
  if (!selectedRoleId.value) return;
  savingPermissions.value = true;
  try {
    await RoleAPI.update(selectedRoleId.value, {
      menu_ids: checkedMenuIds.value,
    });
    Toast.success("权限分配成功");
    originalCheckedIds.value = [...checkedMenuIds.value];
    fetchRoles(); // Refresh role list to get updated menus
  } catch (err: any) {
    Toast.error(err.message || "权限保存失败");
  } finally {
    savingPermissions.value = false;
  }
}
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: var(--semi-color-fill-1);
  border-radius: 20px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background-color: var(--semi-color-fill-2);
}
</style>
