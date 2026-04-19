<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader title="菜单管理" description="系统菜单树及按钮级权限码管理" icon="heroicons:list-bullet" />

    <ProTable :columns="columns" :data="flatData" :loading="loading" :page-size="0" empty-content="暂无菜单数据">
      <template #toolbar-left>
        <NInput v-model:value="searchText" placeholder="搜索菜单名称 / 标识码…" style="width: 260px" clearable>
          <template #prefix><Icon name="heroicons:magnifying-glass" class="w-4 h-4" /></template>
        </NInput>
      </template>
      <template #toolbar-right>
        <NButton type="primary" @click="openModal(null)">
          <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
          新建顶级菜单
        </NButton>
      </template>
    </ProTable>

    <CrudModal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑菜单' : (selectedParentName ? `添加子菜单 · ${selectedParentName}` : '新建顶级菜单')"
      :loading="saving"
      :width="500"
      @confirm="submitForm"
    >
      <NForm ref="formRef" :model="formData" :rules="formRules" label-placement="left" :label-width="88">
        <NFormItem path="type" label="节点类型">
          <NSelect v-model:value="formData.type" :options="typeOptions" :disabled="isEdit" />
        </NFormItem>
        <NFormItem path="name" label="名称">
          <NInput v-model:value="formData.name" placeholder="例如：用户管理" />
        </NFormItem>
        <NFormItem path="code" label="标识码">
          <NInput v-model:value="formData.code" placeholder="例如：platform:users" />
        </NFormItem>
        <NFormItem path="path" label="路由路径">
          <NInput v-model:value="formData.path" placeholder="前端路由，仅目录/菜单需要" />
        </NFormItem>
        <NFormItem path="icon" label="图标">
          <IconPicker v-model="formData.icon" style="width: 100%" />
        </NFormItem>
        <NFormItem path="sort_order" label="排序号">
          <NInputNumber v-model:value="formData.sort_order" :min="0" style="width: 100%" />
        </NFormItem>
        <NFormItem path="is_visible" label="侧边栏可见">
          <NSwitch v-model:value="formData.is_visible" />
        </NFormItem>
      </NForm>
    </CrudModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted, reactive, h } from "vue";
import {
  NButton, NInput, NInputNumber, NSelect, NSwitch, NForm, NFormItem,
  NTag, useMessage, useDialog,
} from "naive-ui";
import type { FormInst } from "naive-ui";
import { TrashIcon, PencilIcon, PlusIcon } from "@heroicons/vue/24/outline";
import { MenuAPI, type MenuTree, type Menu } from "@/api/iam";
import AdminPageHeader from "@/components/admin/PageHeader.vue";
import ProTable from "@/components/ui/ProTable.vue";
import CrudModal from "@/components/ui/CrudModal.vue";
import IconPicker from "@/components/ui/IconPicker.vue";

definePageMeta({ layout: "admin", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();

// ── 数据 ──────────────────────────────────────────────────────────
const menuTree = ref<MenuTree[]>([]);
const loading = ref(false);
const searchText = ref("");

const typeOptions = [
  { label: "目录 (DIR)", value: "DIR" },
  { label: "菜单 (MENU)", value: "MENU" },
  { label: "按钮权限 (BUTTON)", value: "BUTTON" },
];

/** 过滤树，保留匹配节点及其祖先 */
function filterTree(nodes: MenuTree[], q: string): MenuTree[] {
  if (!q) return nodes;
  const lq = q.toLowerCase();
  return nodes.reduce<MenuTree[]>((acc, node) => {
    const matchSelf = node.name.toLowerCase().includes(lq) || node.code.toLowerCase().includes(lq);
    const filteredChildren = filterTree(node.children ?? [], q);
    if (matchSelf || filteredChildren.length > 0) {
      acc.push({ ...node, children: filteredChildren });
    }
    return acc;
  }, []);
}

/** 树形结构扁平化，附带缩进层级 */
interface FlatMenu extends MenuTree { _level: number }

function flattenTree(nodes: MenuTree[], level = 0): FlatMenu[] {
  return nodes.flatMap((node) => [
    { ...node, _level: level },
    ...flattenTree(node.children ?? [], level + 1),
  ]);
}

const flatData = computed(() =>
  flattenTree(filterTree(menuTree.value, searchText.value.trim())),
);

onMounted(fetchMenus);

async function fetchMenus() {
  loading.value = true;
  try {
    const res = (await MenuAPI.tree()) as any;
    menuTree.value = res.data ?? [];
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "获取菜单失败");
  } finally {
    loading.value = false;
  }
}

// ── 表格列 ────────────────────────────────────────────────────────
const TYPE_COLOR: Record<string, "info" | "success" | "warning"> = {
  DIR: "info", MENU: "success", BUTTON: "warning",
};
const TYPE_LABEL: Record<string, string> = { DIR: "目录", MENU: "菜单", BUTTON: "按钮" };

const columns = [
  {
    title: "名称", key: "name", width: 300,
    render: (row: FlatMenu) => (
      <div class="flex items-center gap-2 py-0.5" style={{ paddingLeft: `${row._level * 20 + 4}px` }}>
        {row._level > 0 && (
          <span class="text-[10px] select-none" style="color:var(--semi-color-text-3)">└</span>
        )}
        <NTag type={TYPE_COLOR[row.type] ?? "default"} size="small" style="flex-shrink:0">
          {TYPE_LABEL[row.type] ?? row.type}
        </NTag>
        <span
          class="text-[13px] truncate"
          style={`color:var(--semi-color-text-${row.type === "DIR" ? "0" : "1"});font-weight:${row.type === "DIR" ? "600" : "400"}`}
        >
          {row.name}
        </span>
      </div>
    ),
  },
  {
    title: "标识码", key: "code",
    render: (row: FlatMenu) => (
      <span class="font-mono text-[12px]" style="color:var(--semi-color-text-2)">{row.code}</span>
    ),
  },
  {
    title: "路由路径", key: "path",
    render: (row: FlatMenu) => row.path
      ? <span class="text-[12px]" style="color:var(--semi-color-text-1)">{row.path}</span>
      : <span style="color:var(--semi-color-text-3)">—</span>,
  },
  {
    title: "排序", key: "sort_order", width: 70,
    render: (row: FlatMenu) => (
      <span class="text-[12px]" style="color:var(--semi-color-text-2)">{row.sort_order}</span>
    ),
  },
  {
    title: "可见", key: "is_visible", width: 70,
    render: (row: FlatMenu) => (
      <NTag type={row.is_visible ? "success" : "default"} size="small">
        {row.is_visible ? "是" : "否"}
      </NTag>
    ),
  },
  {
    title: "操作", key: "_actions", width: 190,
    render: (row: FlatMenu) => (
      <div class="flex items-center gap-3">
        {row.type !== "BUTTON" && (
          <NButton
            text size="small"
            onClick={() => openModal(null, row.id, row.name)}
          >
            {{
              icon: () => h(PlusIcon, { class: "w-3.5 h-3.5" }),
              default: () => "子节点",
            }}
          </NButton>
        )}
        <NButton
          text type="primary" size="small"
          onClick={() => openModal(row)}
        >
          {{
            icon: () => h(PencilIcon, { class: "w-3.5 h-3.5" }),
            default: () => "编辑",
          }}
        </NButton>
        <NButton
          text type="error" size="small"
          disabled={row.is_system}
          onClick={() => { if (!row.is_system) handleDelete(row); }}
        >
          {{
            icon: () => h(TrashIcon, { class: "w-3.5 h-3.5" }),
            default: () => "删除",
          }}
        </NButton>
      </div>
    ),
  },
];

// ── 新增 / 编辑 modal ─────────────────────────────────────────────
const modalVisible = ref(false);
const isEdit = ref(false);
const saving = ref(false);
const currentId = ref("");
const selectedParentId = ref<string | undefined>(undefined);
const selectedParentName = ref("");
const formRef = ref<FormInst | null>(null);

const formData = reactive({
  name: "", code: "", type: "DIR" as "DIR" | "MENU" | "BUTTON",
  path: "", icon: "", sort_order: 0, is_visible: true,
});

const formRules = {
  type: [{ required: true, message: "请选择节点类型", trigger: "change" }],
  name: [{ required: true, message: "请输入名称", trigger: "blur" }],
  code: [{ required: true, message: "请输入唯一标识", trigger: "blur" }],
};

function submitForm() {
  formRef.value?.validate((errors) => { if (!errors) handleSave(); });
}

function openModal(node: MenuTree | null, parentId?: string, parentName?: string) {
  if (node) {
    isEdit.value = true;
    currentId.value = node.id;
    selectedParentId.value = node.parent_id ?? undefined;
    selectedParentName.value = "";
    Object.assign(formData, {
      name: node.name, code: node.code,
      type: node.type as "DIR" | "MENU" | "BUTTON",
      path: node.path ?? "", icon: node.icon ?? "",
      sort_order: node.sort_order, is_visible: node.is_visible,
    });
  } else {
    isEdit.value = false;
    currentId.value = "";
    selectedParentId.value = parentId;
    selectedParentName.value = parentName ?? "";
    Object.assign(formData, {
      name: "", code: "", type: parentId ? "MENU" : "DIR",
      path: "", icon: "", sort_order: 0, is_visible: true,
    });
  }
  modalVisible.value = true;
}

async function handleSave() {
  saving.value = true;
  try {
    if (isEdit.value) {
      await MenuAPI.update(currentId.value, { ...formData } as Partial<Menu>);
      message.success("更新成功");
    } else {
      await MenuAPI.create({ ...formData, parent_id: selectedParentId.value ?? null } as Partial<Menu>);
      message.success("创建成功");
    }
    modalVisible.value = false;
    fetchMenus();
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "保存失败");
  } finally {
    saving.value = false;
  }
}

function handleDelete(node: MenuTree) {
  if (node.is_system) return;
  dialog.warning({
    title: `确认删除「${node.name}」？`,
    content: "删除后将同步删除所有子节点，此操作不可恢复。",
    positiveText: "确认删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      try {
        await MenuAPI.delete(node.id);
        message.success("删除成功");
        fetchMenus();
      } catch (err: unknown) {
        message.error(err instanceof Error ? err.message : "删除失败");
      }
    },
  });
}
</script>
