<template>
  <div class="flex flex-col gap-4">
    <div
      class="bg-[var(--semi-color-bg-0)] rounded-xl border border-[var(--semi-color-border)] shadow-sm p-6 min-h-[500px]"
    >
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-lg font-semibold text-[var(--semi-color-text-0)]">
          菜单与权限管理
        </h2>
        <Button theme="solid" type="primary" @click="openModal(null)">
          <template #icon><IconPlus /></template>新建顶级菜单
        </Button>
      </div>

      <Table
        :columns="columns"
        :data-source="menus"
        :loading="loading"
        row-key="id"
        :pagination="false"
        empty-text="暂无菜单数据"
        default-expand-all-rows
      />
    </div>

    <!-- 菜单弹窗 -->
    <Modal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑菜单/权限' : '新增菜单/权限'"
      :confirm-loading="saving"
      @ok="handleModalOk"
      @cancel="modalVisible = false"
      style="width: 500px"
    >
      <Form
        class="mt-4"
        :get-form-api="getFormApi"
        :init-values="formData"
        @submit="handleSave"
        label-position="left"
        :label-width="100"
      >
        <Form.Select
          field="type"
          label="节点类型"
          :rules="[{ required: true, message: '请选择节点类型' }]"
          :disabled="isEdit"
          style="width: 100%"
        >
          <Select.Option value="DIR">目录 (DIR)</Select.Option>
          <Select.Option value="MENU">菜单 (MENU)</Select.Option>
          <Select.Option value="BUTTON">按钮/接口 (BUTTON)</Select.Option>
        </Form.Select>

        <!-- Dynamic Fields based on Type -->
        <Form.Input
          field="name"
          label="名称"
          trigger="blur"
          :rules="[{ required: true, message: '请输入名称' }]"
          placeholder="例如: 用户管理 / 新增用户"
        />

        <Form.Input
          field="code"
          label="标识 (Code)"
          trigger="blur"
          :rules="[{ required: true, message: '请输入唯一英文字母标识' }]"
          placeholder="例如: sys:user / sys:user:add"
        />

        <Form.Input
          field="path"
          label="路由路径"
          placeholder="前端路由(仅目录/菜单需要), 例如: /admin/users"
        />

        <Form.Input
          field="icon"
          label="图标"
          placeholder="组件库 Icon 名称 (例如: IconUserGroup)"
        />

        <Form.InputNumber
          field="sort_order"
          label="排序"
          :rules="[{ required: true, message: '请填写排序' }]"
          style="width: 100%"
        />

        <Form.Switch field="is_visible" label="是否可见" />
      </Form>
    </Modal>
  </div>
</template>

<script setup lang="tsx">
import { ref, onMounted } from "vue";
import {
  Button,
  Table,
  Modal,
  Form,
  Select,
  Toast,
  Tag,
} from "@kousum/semi-ui-vue";
import { IconPlus, IconEdit, IconDelete } from "@kousum/semi-icons-vue";
import { MenuAPI, type MenuTree, type Menu } from "@/api/iam";

definePageMeta({ layout: "admin", middleware: "auth" });

const menus = ref<MenuTree[]>([]);
const loading = ref(false);

const columns = [
  {
    title: "名称",
    dataIndex: "name",
    width: 250,
  },
  {
    title: "标识 (Code)",
    dataIndex: "code",
    width: 200,
  },
  {
    title: "类型",
    dataIndex: "type",
    width: 100,
    render: (val: string) => {
      const colorMap: Record<string, string> = {
        DIR: "blue",
        MENU: "green",
        BUTTON: "orange",
      };
      const textMap: Record<string, string> = {
        DIR: "目录",
        MENU: "菜单",
        BUTTON: "按钮",
      };
      return <Tag color={colorMap[val] || "grey"}>{textMap[val] || val}</Tag>;
    },
  },
  { title: "排序", dataIndex: "sort_order", width: 80 },
  { title: "路径 / Path", dataIndex: "path", width: 200 },
  {
    title: "是否可见",
    dataIndex: "is_visible",
    width: 100,
    render: (val: boolean) => (
      <Tag color={val ? "green" : "red"}>{val ? "显示" : "隐藏"}</Tag>
    ),
  },
  {
    title: "操作",
    dataIndex: "actions",
    render: (_text: unknown, record: unknown) => {
      const node = record as MenuTree;
      return (
        <div class="flex gap-1 items-center">
          {node.type !== "BUTTON" && (
            <Button
              theme="borderless"
              size="small"
              icon={<IconPlus />}
              onClick={() => openModal(null, node.id)}
            >
              添加下级
            </Button>
          )}
          <Button
            theme="borderless"
            type="primary"
            size="small"
            icon={<IconEdit />}
            onClick={() => openModal(node)}
          >
            编辑
          </Button>
          {!node.is_system && (
            <Button
              theme="borderless"
              type="danger"
              size="small"
              icon={<IconDelete />}
              onClick={() => handleDelete(node.id)}
            >
              删除
            </Button>
          )}
          {node.is_system && (
            <Tag color="red" size="small" class="ml-1">
              系统
            </Tag>
          )}
        </div>
      );
    },
  },
];

onMounted(() => {
  fetchMenus();
});

async function fetchMenus() {
  loading.value = true;
  try {
    const res = await MenuAPI.tree();
    menus.value = (res as { data?: MenuTree[] }).data || [];
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "获取菜单失败";
    Toast.error(msg);
  } finally {
    loading.value = false;
  }
}

// ---- Modal Logic ----
const modalVisible = ref(false);
const isEdit = ref(false);
const saving = ref(false);
const currentId = ref("");
const currentParentId = ref<string | undefined>(undefined);

const formApi = ref<{ submitForm: () => void } | null>(null);

function getFormApi(api: { submitForm: () => void }) {
  formApi.value = api;
}

const formData = ref<{
  name: string;
  code: string;
  type: "DIR" | "MENU" | "BUTTON";
  path?: string;
  icon?: string;
  sort_order: number;
  is_visible: boolean;
}>({
  name: "",
  code: "",
  type: "DIR",
  path: "",
  icon: "",
  sort_order: 1,
  is_visible: true,
});

function openModal(node: MenuTree | null, parentId?: string) {
  if (node) {
    isEdit.value = true;
    currentId.value = node.id;
    currentParentId.value = node.parent_id;
    formData.value = {
      name: node.name,
      code: node.code,
      type: node.type,
      path: node.path || "",
      icon: node.icon || "",
      sort_order: node.sort_order,
      is_visible: node.is_visible,
    };
  } else {
    isEdit.value = false;
    currentId.value = "";
    currentParentId.value = parentId; // Set if adding to a specific node
    formData.value = {
      name: "",
      code: "",
      type: parentId ? "MENU" : "DIR", // Default to MENU if child, else DIR
      path: "",
      icon: "",
      sort_order: 1,
      is_visible: true,
    };
  }
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
      await MenuAPI.update(currentId.value, values as Partial<Menu>);
      Toast.success("更新成功");
    } else {
      await MenuAPI.create({
        ...values,
        parent_id: currentParentId.value,
      } as Partial<Menu>);
      Toast.success("创建成功");
    }
    modalVisible.value = false;
    fetchMenus();
  } catch (err: unknown) {
    const msg = err instanceof Error ? err.message : "保存失败";
    Toast.error(msg);
  } finally {
    saving.value = false;
  }
}

function handleDelete(id: string) {
  Modal.warning({
    title: "确认删除？",
    content: "删除节点将同步删除所有子节点，操作不可恢复！",
    onOk: async () => {
      try {
        await MenuAPI.delete(id);
        Toast.success("删除成功");
        fetchMenus();
      } catch (err: unknown) {
        const msg = err instanceof Error ? err.message : "删除失败";
        Toast.error(msg);
      }
    },
  });
}
</script>
