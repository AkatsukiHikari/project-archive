<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="数据字典"
      description="管理系统全局下拉选项，供字段设计等功能引用"
      icon="heroicons:book-open"
    />

    <div class="dict-layout">
      <!-- 左侧：字典类型列表 -->
      <div class="dict-sidebar">
        <div class="dict-sidebar-header">
          <span class="dict-sidebar-title">字典列表</span>
          <NButton size="small" type="primary" ghost @click="openDictModal(null)">
            <template #icon><Icon name="heroicons:plus" class="w-3.5 h-3.5" /></template>
            新增
          </NButton>
        </div>

        <div class="dict-search">
          <NInput
            v-model:value="dictSearch"
            size="small"
            placeholder="搜索字典…"
            clearable
          >
            <template #prefix><Icon name="heroicons:magnifying-glass" class="w-3.5 h-3.5" /></template>
          </NInput>
        </div>

        <div v-if="dictsLoading" class="dict-loading">
          <NSpin size="small" />
        </div>

        <div v-else class="dict-list">
          <div
            v-for="d in filteredDicts"
            :key="d.dict_type"
            class="dict-item"
            :class="{ 'dict-item--active': activeDictType === d.dict_type }"
            @click="selectDict(d)"
          >
            <div class="dict-item-info">
              <div class="flex items-center gap-1.5">
                <span class="dict-item-name">{{ d.dict_name }}</span>
                <NTag v-if="d.is_builtin" size="tiny" type="info" :bordered="false">内置</NTag>
              </div>
              <code class="dict-item-code">{{ d.dict_type }}</code>
            </div>
            <div class="dict-item-right">
              <span class="dict-item-count">{{ d.item_count }} 项</span>
              <NDropdown
                v-if="!d.is_builtin"
                trigger="click"
                :options="dictActions(d)"
                @select="(k: string) => handleDictAction(k, d)"
              >
                <NButton text size="tiny" @click.stop>
                  <Icon name="heroicons:ellipsis-vertical" class="w-4 h-4" />
                </NButton>
              </NDropdown>
            </div>
          </div>

          <div v-if="filteredDicts.length === 0" class="dict-empty">
            {{ dictSearch ? '无匹配字典' : '暂无字典' }}
          </div>
        </div>
      </div>

      <!-- 右侧：字典项管理 -->
      <div class="dict-content">
        <template v-if="activeDict">
          <div class="dict-content-header">
            <div>
              <div class="flex items-center gap-2">
                <span class="dict-content-title">{{ activeDict.dict_name }}</span>
                <NTag v-if="activeDict.is_builtin" type="info" size="small" :bordered="false">系统内置</NTag>
                <code class="dict-type-badge">{{ activeDict.dict_type }}</code>
              </div>
              <p v-if="activeDict.description" class="dict-content-desc">{{ activeDict.description }}</p>
            </div>
            <NButton type="primary" size="small" @click="openItemModal(null)">
              <template #icon><Icon name="heroicons:plus" class="w-3.5 h-3.5" /></template>
              添加字典项
            </NButton>
          </div>

          <ProTable
            :columns="itemColumns"
            :data="items"
            :loading="itemsLoading"
            :page-size="0"
            empty-content="暂无字典项"
          />
        </template>

        <div v-else class="dict-placeholder">
          <Icon name="heroicons:book-open" class="w-12 h-12 opacity-20" />
          <p>← 从左侧选择一个字典查看详情</p>
        </div>
      </div>
    </div>

    <!-- 新增/编辑字典弹窗 -->
    <CrudModal
      v-model:visible="dictModalVisible"
      :title="editingDict ? '编辑字典' : '新增字典'"
      :loading="dictSaving"
      :width="460"
      @confirm="saveDictForm"
    >
      <NForm ref="dictFormRef" :model="dictForm" :rules="dictRules" label-placement="top">
        <NFormItem path="dict_type" label="字典代码">
          <NInput
            v-model:value="dictForm.dict_type"
            :disabled="!!editingDict"
            placeholder="全大写字母+下划线，如 MY_DICT"
          />
        </NFormItem>
        <NFormItem path="dict_name" label="字典名称">
          <NInput v-model:value="dictForm.dict_name" placeholder="中文描述名，如 我的字典" />
        </NFormItem>
        <NFormItem label="说明">
          <NInput v-model:value="dictForm.description" type="textarea" :rows="2" placeholder="可选" />
        </NFormItem>
        <NFormItem label="排序号">
          <NInputNumber v-model:value="dictForm.sort_order" :min="0" class="w-full" />
        </NFormItem>
      </NForm>
    </CrudModal>

    <!-- 新增/编辑字典项弹窗 -->
    <CrudModal
      v-model:visible="itemModalVisible"
      :title="editingItem ? '编辑字典项' : '添加字典项'"
      :loading="itemSaving"
      :width="440"
      @confirm="saveItemForm"
    >
      <NForm ref="itemFormRef" :model="itemForm" :rules="itemRules" label-placement="top">
        <div class="grid grid-cols-2 gap-4">
          <NFormItem path="item_value" label="存储值">
            <NInput v-model:value="itemForm.item_value" placeholder="实际存入数据库的值" />
          </NFormItem>
          <NFormItem path="item_label" label="显示标签">
            <NInput v-model:value="itemForm.item_label" placeholder="界面上展示的文字" />
          </NFormItem>
        </div>
        <NFormItem label="备注">
          <NInput v-model:value="itemForm.description" placeholder="可选" />
        </NFormItem>
        <div class="grid grid-cols-2 gap-4">
          <NFormItem label="排序号">
            <NInputNumber v-model:value="itemForm.sort_order" :min="0" class="w-full" />
          </NFormItem>
          <NFormItem label="默认选中">
            <NSwitch v-model:value="itemForm.is_default" />
          </NFormItem>
        </div>
      </NForm>
    </CrudModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted, reactive } from "vue";
import {
  NButton, NInput, NInputNumber, NSwitch, NTag, NDropdown,
  NForm, NFormItem, NSpin, useMessage, useDialog,
} from "naive-ui";
import type { FormInst, DataTableColumns, DropdownOption } from "naive-ui";
import {
  DictAPI,
  type SysDictSimple,
  type DictItem,
} from "@/api/dict";
import { AdminPageHeader } from "@/components/admin";
import { ProTable, CrudModal  } from "@/components/ui";

definePageMeta({ layout: "admin", middleware: "auth" });

const message = useMessage();
const dialog  = useDialog();

// ── 字典类型列表 ───────────────────────────────────────────────────────────────

const dicts       = ref<SysDictSimple[]>([]);
const dictsLoading = ref(false);
const dictSearch   = ref("");

const filteredDicts = computed(() => {
  const q = dictSearch.value.trim().toLowerCase();
  if (!q) return dicts.value;
  return dicts.value.filter(
    (d) => d.dict_name.toLowerCase().includes(q) || d.dict_type.toLowerCase().includes(q),
  );
});

async function loadDicts() {
  dictsLoading.value = true;
  try {
    const res  = await DictAPI.list();
    dicts.value = res.data;
  } finally {
    dictsLoading.value = false;
  }
}

// ── 选中字典 ───────────────────────────────────────────────────────────────────

const activeDictType = ref<string | null>(null);
const activeDict     = computed(() =>
  dicts.value.find((d) => d.dict_type === activeDictType.value) ?? null,
);

async function selectDict(d: SysDictSimple) {
  activeDictType.value = d.dict_type;
  await loadItems(d.dict_type);
}

// ── 字典项列表 ────────────────────────────────────────────────────────────────

const items        = ref<DictItem[]>([]);
const itemsLoading = ref(false);

async function loadItems(dict_type: string) {
  itemsLoading.value = true;
  try {
    const res = await DictAPI.listItems(dict_type);
    items.value = res.data;
  } finally {
    itemsLoading.value = false;
  }
}

const itemColumns: DataTableColumns<DictItem> = [
  {
    title: "排序",
    key: "sort_order",
    width: 60,
    align: "center",
    render: (row) => <span style="color: var(--n-text-color-3); font-size: 12px">{row.sort_order}</span>,
  },
  {
    title: "存储值",
    key: "item_value",
    width: 160,
    render: (row) => <code style="font-size: 12px">{row.item_value}</code>,
  },
  { title: "显示标签", key: "item_label" },
  {
    title: "默认",
    key: "is_default",
    width: 70,
    align: "center",
    render: (row) =>
      row.is_default
        ? <NTag size="small" type="success" bordered={false}>默认</NTag>
        : <span>—</span>,
  },
  { title: "备注", key: "description", ellipsis: { tooltip: true } },
  {
    title: "操作",
    key: "actions",
    width: 120,
    render: (row) => (
      <div class="flex items-center gap-1 flex-nowrap">
        <NButton size="small" onClick={() => openItemModal(row)}>编辑</NButton>
        <NButton size="small" type="error" onClick={() => confirmDeleteItem(row)}>删除</NButton>
      </div>
    ),
  },
];

// ── 字典类型 CRUD ─────────────────────────────────────────────────────────────

const dictModalVisible = ref(false);
const dictSaving       = ref(false);
const editingDict      = ref<SysDictSimple | null>(null);
const dictFormRef      = ref<FormInst | null>(null);

const dictForm = reactive({
  dict_type: "",
  dict_name: "",
  description: "",
  sort_order: 0,
});

const dictRules = {
  dict_type: [{ required: true, message: "请输入字典代码", trigger: "blur" }],
  dict_name: [{ required: true, message: "请输入字典名称", trigger: "blur" }],
};

function openDictModal(d: SysDictSimple | null) {
  editingDict.value = d;
  Object.assign(dictForm, d
    ? { dict_type: d.dict_type, dict_name: d.dict_name, description: d.description ?? "", sort_order: d.sort_order }
    : { dict_type: "", dict_name: "", description: "", sort_order: 0 },
  );
  dictModalVisible.value = true;
}

async function saveDictForm() {
  await dictFormRef.value?.validate();
  dictSaving.value = true;
  try {
    if (editingDict.value) {
      await DictAPI.update(editingDict.value.dict_type, {
        dict_name: dictForm.dict_name,
        description: dictForm.description || undefined,
        sort_order: dictForm.sort_order,
      });
      message.success("已更新");
    } else {
      await DictAPI.create({
        dict_type: dictForm.dict_type,
        dict_name: dictForm.dict_name,
        description: dictForm.description || undefined,
        sort_order: dictForm.sort_order,
      });
      message.success("已创建");
    }
    dictModalVisible.value = false;
    await loadDicts();
  } finally {
    dictSaving.value = false;
  }
}

function dictActions(d: SysDictSimple): DropdownOption[] {
  return [
    { label: "编辑", key: "edit" },
    { label: "删除", key: "delete", props: { style: "color: var(--n-error-color)" } },
  ];
}

function handleDictAction(key: string, d: SysDictSimple) {
  if (key === "edit") openDictModal(d);
  if (key === "delete") confirmDeleteDict(d);
}

function confirmDeleteDict(d: SysDictSimple) {
  dialog.warning({
    title: "删除字典",
    content: `确定删除字典「${d.dict_name}」及其所有字典项？`,
    positiveText: "确认删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await DictAPI.remove(d.dict_type);
      message.success("已删除");
      if (activeDictType.value === d.dict_type) {
        activeDictType.value = null;
        items.value = [];
      }
      await loadDicts();
    },
  });
}

// ── 字典项 CRUD ───────────────────────────────────────────────────────────────

const itemModalVisible = ref(false);
const itemSaving       = ref(false);
const editingItem      = ref<DictItem | null>(null);
const itemFormRef      = ref<FormInst | null>(null);

const itemForm = reactive({
  item_value: "",
  item_label: "",
  description: "",
  sort_order: 0,
  is_default: false,
});

const itemRules = {
  item_value: [{ required: true, message: "请输入存储值", trigger: "blur" }],
  item_label: [{ required: true, message: "请输入显示标签", trigger: "blur" }],
};

function openItemModal(item: DictItem | null) {
  editingItem.value = item;
  Object.assign(itemForm, item
    ? { item_value: item.item_value, item_label: item.item_label, description: item.description ?? "", sort_order: item.sort_order, is_default: item.is_default }
    : { item_value: "", item_label: "", description: "", sort_order: items.value.length * 10, is_default: false },
  );
  itemModalVisible.value = true;
}

async function saveItemForm() {
  await itemFormRef.value?.validate();
  if (!activeDictType.value) return;
  itemSaving.value = true;
  try {
    if (editingItem.value) {
      await DictAPI.updateItem(editingItem.value.id, {
        item_value: itemForm.item_value,
        item_label: itemForm.item_label,
        description: itemForm.description || undefined,
        sort_order: itemForm.sort_order,
        is_default: itemForm.is_default,
      });
      message.success("已更新");
    } else {
      await DictAPI.createItem(activeDictType.value, {
        item_value: itemForm.item_value,
        item_label: itemForm.item_label,
        description: itemForm.description || undefined,
        sort_order: itemForm.sort_order,
        is_default: itemForm.is_default,
      });
      message.success("已添加");
    }
    itemModalVisible.value = false;
    await loadItems(activeDictType.value);
    await loadDicts(); // 刷新 item_count
  } finally {
    itemSaving.value = false;
  }
}

function confirmDeleteItem(item: DictItem) {
  dialog.warning({
    title: "删除字典项",
    content: `确定删除「${item.item_label}」？`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await DictAPI.removeItem(item.id);
      message.success("已删除");
      if (activeDictType.value) await loadItems(activeDictType.value);
      await loadDicts();
    },
  });
}

onMounted(loadDicts);
</script>

<style scoped>
/* ── 两栏布局 ────────────────────────────────────────────────────────────────── */
.dict-layout {
  display: flex;
  gap: 0;
  min-height: 600px;
  border: 1px solid var(--n-divider-color);
  border-radius: 12px;
  overflow: hidden;
  background: var(--n-card-color);
}

/* ── 左侧边栏 ────────────────────────────────────────────────────────────────── */
.dict-sidebar {
  width: 260px;
  flex-shrink: 0;
  border-right: 1px solid var(--n-divider-color);
  display: flex;
  flex-direction: column;
  background: var(--n-color-embedded);
}

.dict-sidebar-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 14px 10px;
  flex-shrink: 0;
}

.dict-sidebar-title {
  font-size: 13px;
  font-weight: 600;
  color: var(--n-text-color-1);
}

.dict-search {
  padding: 0 10px 10px;
  flex-shrink: 0;
}

.dict-loading {
  display: flex;
  justify-content: center;
  padding: 24px;
}

.dict-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 6px 12px;
}

.dict-item {
  display: flex;
  align-items: center;
  padding: 8px 10px;
  border-radius: 7px;
  cursor: pointer;
  gap: 6px;
  transition: background .12s;
}

.dict-item:hover {
  background: var(--n-card-color);
}

.dict-item--active {
  background: color-mix(in srgb, var(--n-primary-color) 10%, transparent);
}

.dict-item--active .dict-item-name {
  color: var(--n-primary-color);
  font-weight: 600;
}

.dict-item-info {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
  gap: 2px;
}

.dict-item-name {
  font-size: 13px;
  color: var(--n-text-color-1);
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}

.dict-item-code {
  font-size: 10px;
  color: var(--n-text-color-3);
  font-family: 'Fira Code', monospace;
}

.dict-item-right {
  display: flex;
  align-items: center;
  gap: 4px;
  flex-shrink: 0;
}

.dict-item-count {
  font-size: 11px;
  color: var(--n-text-color-3);
}

.dict-empty {
  text-align: center;
  color: var(--n-text-color-3);
  font-size: 13px;
  padding: 24px 0;
}

/* ── 右侧内容 ────────────────────────────────────────────────────────────────── */
.dict-content {
  flex: 1;
  min-width: 0;
  display: flex;
  flex-direction: column;
}

.dict-content-header {
  display: flex;
  align-items: flex-start;
  justify-content: space-between;
  padding: 16px 20px 12px;
  border-bottom: 1px solid var(--n-divider-color);
  gap: 12px;
}

.dict-content-title {
  font-size: 15px;
  font-weight: 600;
  color: var(--n-text-color-1);
}

.dict-type-badge {
  font-size: 11px;
  padding: 2px 6px;
  border-radius: 4px;
  background: var(--n-color-embedded);
  color: var(--n-text-color-3);
  font-family: 'Fira Code', monospace;
}

.dict-content-desc {
  margin-top: 3px;
  font-size: 12px;
  color: var(--n-text-color-3);
}

.dict-placeholder {
  flex: 1;
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 10px;
  color: var(--n-text-color-3);
  font-size: 13px;
}
</style>
