<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="档案门类"
      description="管理档案分类体系及各门类的自定义字段 schema"
      icon="heroicons:tag"
    />

    <ProTable
      :columns="columns"
      :data="categories"
      :loading="loading"
      empty-content="暂无门类数据"
      :page-size="0"
    >
      <template #toolbar-right>
        <NButton type="primary" @click="openModal(null)">
          <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
          新增门类
        </NButton>
      </template>
    </ProTable>

    <CrudModal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑门类' : '新增门类'"
      :loading="saving"
      :width="480"
      @confirm="submitForm"
    >
      <NForm ref="formRef" :model="formData" :rules="rules" label-placement="left" :label-width="90">
        <NFormItem path="code" label="门类代码">
          <NInput v-model:value="formData.code" :disabled="isEdit" placeholder="如 WS（不可修改）" />
        </NFormItem>
        <NFormItem path="name" label="门类名称">
          <NInput v-model:value="formData.name" placeholder="如 文书档案" />
        </NFormItem>
        <NFormItem path="parent_id" label="父门类">
          <NSelect
            v-model:value="formData.parent_id"
            :options="parentOptions"
            placeholder="顶级门类（不选）"
            clearable
          />
        </NFormItem>
        <NFormItem label="隐私保护">
          <NSwitch v-model:value="formData.requires_privacy_guard" />
          <span class="ml-2 text-sm text-gray-500">含个人隐私字段时开启</span>
        </NFormItem>
      </NForm>
    </CrudModal>

    <!-- 克隆门类弹窗 -->
    <NModal v-model:show="cloneVisible" preset="dialog" title="克隆门类">
      <NForm label-placement="left" :label-width="80">
        <NFormItem label="新门类代码">
          <NInput v-model:value="cloneForm.code" placeholder="新的唯一代码" />
        </NFormItem>
        <NFormItem label="新门类名称">
          <NInput v-model:value="cloneForm.name" placeholder="新门类名称" />
        </NFormItem>
      </NForm>
      <template #action>
        <NButton @click="cloneVisible = false">取消</NButton>
        <NButton type="primary" :loading="saving" @click="submitClone">克隆</NButton>
      </template>
    </NModal>

    <!-- 字段 Schema 编辑抽屉 -->
    <NDrawer v-model:show="schemaVisible" :width="640" placement="right">
      <NDrawerContent :title="`字段设计 — ${schemaCategory?.name}`" closable>
        <div class="flex flex-col gap-3">
          <div
            v-for="(field, idx) in schemaFields"
            :key="idx"
            class="border rounded-lg p-3 flex flex-col gap-2"
            :style="field.inherited ? 'background:#f5f5f5' : ''"
          >
            <div class="flex items-center gap-2">
              <NTag v-if="field.inherited" size="small" type="warning">继承</NTag>
              <span class="font-medium text-sm">{{ field.label }}</span>
              <span class="text-xs text-gray-400">{{ field.name }}</span>
              <span class="ml-auto">
                <NTag size="small">{{ field.type }}</NTag>
              </span>
              <NButton
                v-if="!field.inherited"
                size="tiny"
                type="error"
                @click="schemaFields.splice(idx, 1)"
              >
                删除
              </NButton>
            </div>
            <div v-if="!field.inherited" class="grid grid-cols-2 gap-2">
              <NFormItem label="显示标签" :show-label="true" size="small">
                <NInput v-model:value="field.label" size="small" />
              </NFormItem>
              <NFormItem label="字段 key" :show-label="true" size="small">
                <NInput v-model:value="field.name" size="small" />
              </NFormItem>
              <NFormItem label="类型" :show-label="true" size="small">
                <NSelect v-model:value="field.type" :options="fieldTypeOptions" size="small" />
              </NFormItem>
              <NFormItem label="必填" :show-label="true" size="small">
                <NSwitch v-model:value="field.required" size="small" />
              </NFormItem>
            </div>
          </div>
          <NButton dashed @click="addField">
            <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
            添加字段
          </NButton>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <NButton @click="schemaVisible = false">取消</NButton>
            <NButton type="primary" :loading="schemaSaving" @click="saveSchema">保存 Schema</NButton>
          </div>
        </template>
      </NDrawerContent>
    </NDrawer>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted, reactive } from "vue";
import {
  NButton, NInput, NSelect, NSwitch, NForm, NFormItem, NTag, NSpace,
  NModal, NDrawer, NDrawerContent, useMessage, useDialog,
} from "naive-ui";
import type { FormInst, DataTableColumns } from "naive-ui";
import { CategoryAPI, type ArchiveCategory, type FieldDefinition } from "@/api/repository";
import AdminPageHeader from "@/components/admin/PageHeader.vue";
import ProTable from "@/components/ui/ProTable.vue";
import CrudModal from "@/components/ui/CrudModal.vue";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();

const categories = ref<ArchiveCategory[]>([]);
const loading = ref(false);

const parentOptions = computed(() =>
  categories.value.map((c) => ({ label: `${c.code} - ${c.name}`, value: c.id })),
);

const fieldTypeOptions = [
  { label: "文本", value: "text" },
  { label: "数字", value: "number" },
  { label: "日期", value: "date" },
  { label: "下拉", value: "select" },
  { label: "开关", value: "boolean" },
  { label: "多行文本", value: "textarea" },
];

const columns: DataTableColumns<ArchiveCategory> = [
  { title: "代码", key: "code", width: 100 },
  { title: "名称", key: "name", ellipsis: { tooltip: true } },
  {
    title: "内置",
    key: "is_builtin",
    width: 80,
    render: (row) =>
      row.is_builtin ? <NTag type="info" size="small">系统</NTag> : <span class="text-gray-400 text-xs">自定义</span>,
  },
  {
    title: "隐私保护",
    key: "requires_privacy_guard",
    width: 90,
    render: (row) =>
      row.requires_privacy_guard ? <NTag type="warning" size="small">开启</NTag> : <span>—</span>,
  },
  {
    title: "自定义字段",
    key: "field_schema",
    width: 100,
    render: (row) => <span>{row.field_schema?.length ?? 0} 个</span>,
  },
  {
    title: "操作",
    key: "actions",
    width: 220,
    render: (row) => (
      <NSpace size="small">
        <NButton size="small" onClick={() => openSchemaDrawer(row)}>字段设计</NButton>
        {!row.is_builtin && (
          <>
            <NButton size="small" onClick={() => openClone(row)}>克隆</NButton>
            <NButton size="small" onClick={() => openModal(row)}>编辑</NButton>
            <NButton size="small" type="error" onClick={() => confirmDelete(row)}>删除</NButton>
          </>
        )}
      </NSpace>
    ),
  },
];

const modalVisible = ref(false);
const saving = ref(false);
const isEdit = ref(false);
const editId = ref<string | null>(null);
const formRef = ref<FormInst | null>(null);

const emptyForm = () => ({
  code: "",
  name: "",
  parent_id: null as string | null,
  requires_privacy_guard: false,
});

const formData = reactive(emptyForm());

const rules = {
  code: [{ required: true, message: "请输入门类代码", trigger: "blur" }],
  name: [{ required: true, message: "请输入门类名称", trigger: "blur" }],
};

function openModal(row: ArchiveCategory | null) {
  if (row) {
    isEdit.value = true;
    editId.value = row.id;
    Object.assign(formData, {
      code: row.code,
      name: row.name,
      parent_id: row.parent_id ?? null,
      requires_privacy_guard: row.requires_privacy_guard,
    });
  } else {
    isEdit.value = false;
    editId.value = null;
    Object.assign(formData, emptyForm());
  }
  modalVisible.value = true;
}

async function submitForm() {
  await formRef.value?.validate();
  saving.value = true;
  try {
    if (isEdit.value && editId.value) {
      await CategoryAPI.update(editId.value, {
        name: formData.name,
        requires_privacy_guard: formData.requires_privacy_guard,
      });
      message.success("已更新");
    } else {
      await CategoryAPI.create({
        code: formData.code,
        name: formData.name,
        parent_id: formData.parent_id ?? undefined,
        requires_privacy_guard: formData.requires_privacy_guard,
      });
      message.success("已创建");
    }
    modalVisible.value = false;
    await loadList();
  } finally {
    saving.value = false;
  }
}

function confirmDelete(row: ArchiveCategory) {
  dialog.warning({
    title: "删除确认",
    content: `确定删除门类「${row.name}」？`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await CategoryAPI.remove(row.id);
      message.success("已删除");
      await loadList();
    },
  });
}

const cloneVisible = ref(false);
const cloneSourceId = ref<string | null>(null);
const cloneForm = reactive({ code: "", name: "" });

function openClone(row: ArchiveCategory) {
  cloneSourceId.value = row.id;
  cloneForm.code = "";
  cloneForm.name = row.name + "（副本）";
  cloneVisible.value = true;
}

async function submitClone() {
  if (!cloneSourceId.value || !cloneForm.code || !cloneForm.name) {
    message.warning("请填写新代码和名称");
    return;
  }
  saving.value = true;
  try {
    await CategoryAPI.clone(cloneSourceId.value, cloneForm.code, cloneForm.name);
    message.success("克隆成功");
    cloneVisible.value = false;
    await loadList();
  } finally {
    saving.value = false;
  }
}

const schemaVisible = ref(false);
const schemaSaving = ref(false);
const schemaCategory = ref<ArchiveCategory | null>(null);
const schemaFields = ref<FieldDefinition[]>([]);

async function openSchemaDrawer(row: ArchiveCategory) {
  schemaCategory.value = row;
  const res = await CategoryAPI.getSchema(row.id);
  schemaFields.value = res.data.data.map((f) => ({ ...f }));
  schemaVisible.value = true;
}

function addField() {
  schemaFields.value.push({
    name: "",
    label: "",
    type: "text",
    required: false,
    inherited: false,
  });
}

async function saveSchema() {
  if (!schemaCategory.value) return;
  schemaSaving.value = true;
  try {
    await CategoryAPI.updateSchema(schemaCategory.value.id, schemaFields.value);
    message.success("Schema 已保存");
    schemaVisible.value = false;
    await loadList();
  } finally {
    schemaSaving.value = false;
  }
}

async function loadList() {
  loading.value = true;
  try {
    const res = await CategoryAPI.list();
    categories.value = res.data.data;
  } finally {
    loading.value = false;
  }
}

onMounted(loadList);
</script>
