<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="档案门类"
      description="管理档案分类体系及各门类的自定义字段 schema"
      icon="heroicons:tag"
    />

    <ProTable
      :columns="columns"
      :data="sortedCategories"
      :loading="loading"
      empty-content="暂无门类数据"
      :checked-row-keys="selectedKeys"
      @update:checked-row-keys="(keys: DataTableRowKey[]) => selectedKeys = keys"
    >
      <template #toolbar-left>
        <NButton
          v-if="selectedKeys.length > 0"
          type="error"
          ghost
          size="small"
          @click="batchDelete"
        >
          <template #icon><Icon name="heroicons:trash" class="w-4 h-4" /></template>
          批量删除 ({{ selectedKeys.length }})
        </NButton>
      </template>
      <template #toolbar-right>
        <NButton type="primary" @click="openModal(null)">
          <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
          新增门类
        </NButton>
      </template>
    </ProTable>

    <!-- 新增 / 编辑弹窗 -->
    <CrudModal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑门类' : '新增门类'"
      :loading="saving"
      :width="480"
      @confirm="submitForm"
    >
      <NForm ref="formRef" :model="formData" :rules="rules" label-placement="left" :label-width="96">
        <NFormItem path="code" label="门类代码">
          <NInput v-model:value="formData.code" :disabled="isEdit" placeholder="如 WS（创建后不可修改）" />
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
      </NForm>
    </CrudModal>

    <!-- 克隆门类弹窗 -->
    <NModal v-model:show="cloneVisible" preset="dialog" title="克隆门类">
      <p class="mb-3 text-sm" style="color: var(--n-text-color-3)">
        克隆将复制原门类的所有字段定义，新门类默认为「自定义」类型
      </p>
      <NForm label-placement="left" :label-width="80">
        <NFormItem label="门类代码">
          <NInput v-model:value="cloneForm.code" placeholder="新的唯一代码" />
        </NFormItem>
        <NFormItem label="门类名称">
          <NInput v-model:value="cloneForm.name" placeholder="新门类名称" />
        </NFormItem>
      </NForm>
      <template #action>
        <NButton @click="cloneVisible = false">取消</NButton>
        <NButton type="primary" :loading="saving" @click="submitClone">确认克隆</NButton>
      </template>
    </NModal>

    <!-- 字段 Schema 编辑抽屉 -->
    <NDrawer v-model:show="schemaVisible" :width="780" placement="right">
      <NDrawerContent closable>
        <template #header>
          <div class="flex items-center gap-2">
            <Icon name="heroicons:table-cells" class="w-4 h-4" style="color: var(--n-primary-color)" />
            <span>字段设计</span>
            <NDivider vertical />
            <span class="text-sm font-normal" style="color: var(--n-text-color-3)">{{ schemaCategory?.name }}</span>
          </div>
        </template>

        <div class="flex flex-col gap-6">

          <!-- ① 通用著录项 -->
          <div>
            <div class="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider opacity-60 px-2.5 py-1.5 mb-3 rounded bg-base-content/5 border border-base-content/15">
              <Icon name="heroicons:lock-closed" class="w-3 h-3" />
              通用著录项
              <NTag size="tiny" type="info" class="ml-1" :bordered="false">DA/T 18-2022</NTag>
              <span class="ml-auto font-normal normal-case tracking-normal opacity-70">字段名不可改；必填与默认值可按门类独立调整</span>
            </div>

            <!-- 三列网格，每格用虚线分隔 -->
            <div class="grid grid-cols-3 gap-2">
              <div
                v-for="field in inheritedFields"
                :key="field.name"
                class="flex flex-col gap-3 p-4 rounded-md border border-dashed border-base-content/15"
              >
                <!-- 字段标识行 -->
                <div class="flex items-baseline gap-1.5">
                  <span class="text-sm font-semibold">{{ field.label }}</span>
                  <code class="text-[10px] font-mono px-1 rounded border border-base-content/15 opacity-50">{{ field.name }}</code>
                  <span class="text-[10px] opacity-40 ml-auto">{{ fieldTypeLabel(field.type) }}</span>
                </div>
                <!-- 控制行 -->
                <div class="flex flex-col gap-2">
                  <div class="flex items-center gap-2">
                    <span class="text-[11px] opacity-50 w-7 shrink-0">必填</span>
                    <NSwitch
                      :value="!!field.required"
                      size="small"
                      @update:value="v => field.required = v"
                    />
                  </div>
                  <div class="flex items-center gap-2">
                    <span class="text-[11px] opacity-50 w-7 shrink-0">默认</span>
                    <span v-if="field.type === 'boolean'" class="text-sm opacity-30">—</span>
                    <NSelect
                      v-else-if="field.type === 'select'"
                      :value="field.default_value != null ? String(field.default_value) : null"
                      :options="dictMap[field.dict_type ?? ''] ?? []"
                      size="small"
                      clearable
                      class="flex-1"
                      @update:value="v => field.default_value = v"
                    />
                    <NInput
                      v-else-if="field.default_value === '$currentYear'"
                      value="当前年度"
                      size="small"
                      disabled
                      class="flex-1"
                    />
                    <NInput
                      v-else
                      :value="field.default_value != null ? String(field.default_value) : ''"
                      size="small"
                      :placeholder="`请输入${field.label}值`"
                      class="flex-1"
                      @update:value="v => field.default_value = v || null"
                    />
                  </div>
                </div>
              </div>
            </div>
          </div>

          <!-- ② 门类私有字段 -->
          <div>
            <div class="flex items-center gap-1.5 text-[11px] font-bold uppercase tracking-wider opacity-60 px-2.5 py-1.5 mb-3 rounded bg-base-content/5 border border-base-content/15">
              <Icon name="heroicons:pencil-square" class="w-3 h-3" />
              门类私有字段
              <span class="ml-auto font-normal normal-case tracking-normal opacity-70">可拖拽调整顺序</span>
            </div>

            <div class="flex flex-col">
              <div
                v-for="(field, idx) in customFieldsLocal"
                :key="field.name || idx"
                class="py-3.5"
                draggable="true"
                :class="{
                  'opacity-40': dragIdx === idx,
                  'border-t-2 border-t-primary': dragOverIdx === idx && dragIdx !== idx,
                  'border-t border-dashed border-base-content/25': idx > 0 && !(dragOverIdx === idx && dragIdx !== idx),
                }"
                @dragstart="onDragStart(idx)"
                @dragenter.prevent="onDragEnter(idx)"
                @dragend="onDragEnd"
                @drop.prevent="onDrop(idx)"
                @dragover.prevent
              >
                <!-- 字段头：序号 + 拖拽 + 删除 -->
                <div class="flex items-center gap-1.5 mb-2.5 pb-2 border-b border-base-content/15">
                  <div class="flex items-center cursor-grab opacity-50 hover:opacity-100 active:cursor-grabbing">
                    <Icon name="heroicons:bars-3" class="w-3.5 h-3.5" />
                  </div>
                  <span class="text-xs font-semibold opacity-60">字段 {{ idx + 1 }}</span>
                  <div class="flex-1" />
                  <NButton size="tiny" type="error" text @click="removeCustomField(idx)">
                    <template #icon><Icon name="heroicons:trash" class="w-3 h-3" /></template>
                    删除
                  </NButton>
                </div>

                <!-- 字段内容：2列网格 -->
                <div class="grid grid-cols-2 gap-x-5 gap-y-2.5">
                  <NFormItem label="显示标签" size="small" :show-feedback="false" label-placement="top">
                    <NInput v-model:value="field.label" size="small" placeholder="中文标签" />
                  </NFormItem>
                  <NFormItem label="字段 Key" size="small" :show-feedback="false" label-placement="top">
                    <NInput v-model:value="field.name" size="small" placeholder="拼音大写缩写" />
                  </NFormItem>
                  <NFormItem label="字段类型" size="small" :show-feedback="false" label-placement="top">
                    <NSelect
                      v-model:value="field.type"
                      :options="fieldTypeOptions"
                      size="small"
                      @update:value="() => { field.default_value = null; field.options = []; }"
                    />
                  </NFormItem>
                  <NFormItem label="必填" size="small" :show-feedback="false" label-placement="top">
                    <div class="h-7 flex items-center">
                      <NSwitch v-model:value="field.required" size="small" />
                    </div>
                  </NFormItem>

                  <!-- select 类型扩展行 -->
                  <template v-if="field.type === 'select'">
                    <NFormItem label="关联字典" size="small" :show-feedback="false" label-placement="top">
                      <NSelect
                        v-model:value="field.dict_type"
                        :options="dictSelectOptions"
                        size="small"
                        clearable
                        placeholder="不关联，自定义选项"
                        @update:value="() => { field.default_value = null; field.options = []; }"
                      />
                    </NFormItem>

                    <NFormItem label="可选项" size="small" :show-feedback="false" label-placement="top">
                      <NSelect
                        v-if="field.dict_type && dictMap[field.dict_type]"
                        :value="null"
                        :options="dictMap[field.dict_type] || []"
                        size="small"
                        disabled
                        placeholder="由字典提供"
                      />
                      <NSelect
                        v-else
                        v-model:value="field.options"
                        multiple
                        tag
                        filterable
                        size="small"
                        placeholder="输入后按 Enter 添加选项"
                        :show-arrow="false"
                      />
                    </NFormItem>

                    <div class="col-span-2">
                      <NFormItem label="默认值" size="small" :show-feedback="false" label-placement="top">
                        <NSelect
                          :value="field.default_value != null ? String(field.default_value) : null"
                          :options="field.dict_type && dictMap[field.dict_type]
                            ? dictMap[field.dict_type]
                            : (field.options || []).map(o => ({ label: o, value: o }))"
                          size="small"
                          clearable
                          placeholder="选择默认值"
                          @update:value="v => field.default_value = v"
                        />
                      </NFormItem>
                    </div>
                  </template>

                  <!-- 非 select：文本默认值 -->
                  <NFormItem
                    v-else
                    label="默认值"
                    size="small"
                    :show-feedback="false"
                    label-placement="top"
                  >
                    <NInput
                      :value="field.default_value != null ? String(field.default_value) : ''"
                      size="small"
                      :placeholder="`请输入${field.label}值`"
                      @update:value="v => field.default_value = v || null"
                    />
                  </NFormItem>
                </div>
              </div>

              <div v-if="customFieldsLocal.length === 0" class="flex items-center justify-center gap-2 p-5 border border-dashed border-base-content/15 rounded-lg text-[13px] opacity-40 mb-3">
                <Icon name="heroicons:inbox" class="w-6 h-6" />
                <span>该门类暂无私有字段，点击下方按钮添加</span>
              </div>

              <NButton dashed class="w-full mt-4" @click="addField">
                <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
                添加私有字段
              </NButton>
            </div>
          </div>
        </div>

        <template #footer>
          <div class="flex items-center gap-3 w-full">
            <NButton secondary @click="goToDesigner">
              <template #icon><Icon name="heroicons:squares-2x2" class="w-4 h-4" /></template>
              录入排版设计
            </NButton>
            <div class="flex-1" />
            <NButton @click="schemaVisible = false">取消</NButton>
            <NButton type="primary" :loading="schemaSaving" @click="saveSchema">保存字段</NButton>
          </div>
        </template>
      </NDrawerContent>
    </NDrawer>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted, reactive, watch } from "vue";
import { useRouter } from "vue-router";
import {
  NButton, NInput, NSelect, NSwitch, NForm, NFormItem, NTag, NDivider,
  NModal, NDrawer, NDrawerContent, useMessage, useDialog,
} from "naive-ui";
import type { FormInst, DataTableColumns, DataTableRowKey } from "naive-ui";
import { CategoryAPI, type ArchiveCategory, type FieldDefinition } from "@/api/repository";
import { DictAPI, type DictItem } from "@/api/dict";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { CrudModal } from "@/components/ui";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const dialog  = useDialog();
const router  = useRouter();

// ── 数据 ──────────────────────────────────────────────────────────────────────

const categories = ref<ArchiveCategory[]>([]);
const loading    = ref(false);

const sortedCategories = computed(() =>
  categories.value.map((c, idx) => ({ ...c, _idx: idx + 1 })),
);

const selectedKeys = ref<DataTableRowKey[]>([]);

const parentOptions = computed(() =>
  categories.value.map((c) => ({ label: `${c.code} — ${c.name}`, value: c.id })),
);

const fieldTypeOptions = [
  { label: "文本",     value: "text"     },
  { label: "数字",     value: "number"   },
  { label: "日期",     value: "date"     },
  { label: "下拉选择", value: "select"   },
  { label: "开关",     value: "boolean"  },
  { label: "多行文本", value: "textarea" },
];

const fieldTypeLabel = (t: string) =>
  fieldTypeOptions.find((o) => o.value === t)?.label ?? t;

// ── 列定义 ────────────────────────────────────────────────────────────────────

type T = ArchiveCategory & { _idx: number };
const columns = ([
  { type: "selection" },
  {
    title: "#",
    key: "_idx",
    width: 46,
    align: "center",
    render: (row) => (
      <span style="color: var(--n-text-color-3); font-size: 12px">{row._idx}</span>
    ),
  },
  {
    title: "代码",
    key: "code",
    width: 96,
    sorter: (a, b) => a.code.localeCompare(b.code),
    search: { placeholder: "搜索代码…" },
    render: (row) => (
      <code style="font-size: 12px; color: var(--n-text-color-2); background: var(--n-color-embedded); padding: 2px 6px; border-radius: 4px">
        {row.code}
      </code>
    ),
  },
  {
    title: "名称",
    key: "name",
    width: 120,
    sorter: (a, b) => a.name.localeCompare(b.name),
    ellipsis: { tooltip: true },
    search: { placeholder: "搜索名称…" },
  },
  {
    title: "类型",
    key: "is_builtin",
    width: 80,
    filterOptions: [
      { label: "系统内置", value: "1" },
      { label: "自定义",   value: "0" },
    ],
    filter: (value, row) => String(row.is_builtin ? "1" : "0") === value,
    render: (row) =>
      row.is_builtin
        ? <NTag size="small" type="info" bordered={false}>系统内置</NTag>
        : <NTag size="small" bordered={false}>自定义</NTag>,
  },
  {
    title: "操作",
    key: "actions",
    width: 220,
    render: (row) => (
      <div class="flex items-center gap-1 flex-nowrap">
        <NButton size="small" onClick={() => openSchemaDrawer(row)}>字段设计</NButton>
        <NButton size="small" onClick={() => goDesigner(row)}>排版设计</NButton>
        {!row.is_builtin && (
          <NButton size="small" onClick={() => openModal(row)}>编辑</NButton>
        )}
        <NButton size="small" onClick={() => openClone(row)}>克隆</NButton>
        <NButton size="small" type="error" onClick={() => confirmDelete(row)}>删除</NButton>
      </div>
    ),
  },
] as DataTableColumns<T>);

// ── CRUD ──────────────────────────────────────────────────────────────────────

const modalVisible = ref(false);
const saving       = ref(false);
const isEdit       = ref(false);
const editId       = ref<string | null>(null);
const formRef      = ref<FormInst | null>(null);

const emptyForm = () => ({
  code: "",
  name: "",
  parent_id: null as string | null,
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
      await CategoryAPI.update(editId.value, { name: formData.name });
      message.success("已更新");
    } else {
      await CategoryAPI.create({
        code: formData.code,
        name: formData.name,
        parent_id: formData.parent_id ?? undefined,
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
  const isBuiltin = row.is_builtin;
  dialog.warning({
    title: "删除确认",
    content: isBuiltin
      ? `「${row.name}」是系统内置门类，删除后如需恢复需重新初始化数据。确定删除？`
      : `确定删除门类「${row.name}」？`,
    positiveText: "确认删除",
    negativeText: "取消",
    type: isBuiltin ? "error" : "warning",
    onPositiveClick: async () => {
      await CategoryAPI.remove(row.id);
      message.success("已删除");
      selectedKeys.value = selectedKeys.value.filter((k) => k !== row.id);
      await loadList();
    },
  });
}

async function batchDelete() {
  if (!selectedKeys.value.length) return;
  dialog.error({
    title: "批量删除确认",
    content: `确定删除已选的 ${selectedKeys.value.length} 个门类？此操作不可恢复。`,
    positiveText: "全部删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await Promise.all(
        (selectedKeys.value as string[]).map((id) => CategoryAPI.remove(id)),
      );
      message.success(`已删除 ${selectedKeys.value.length} 个门类`);
      selectedKeys.value = [];
      await loadList();
    },
  });
}

// ── 克隆 ──────────────────────────────────────────────────────────────────────

const cloneVisible  = ref(false);
const cloneSourceId = ref<string | null>(null);
const cloneForm     = reactive({ code: "", name: "" });

function openClone(row: ArchiveCategory) {
  cloneSourceId.value = row.id;
  cloneForm.code      = "";
  cloneForm.name      = row.name + "（副本）";
  cloneVisible.value  = true;
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

// ── 字典数据（用于字段关联） ──────────────────────────────────────────────────

/** dict_type → SelectOption[] (value/label) */
const dictMap = ref<Record<string, { label: string; value: string }[]>>({});

/** 字典选择器选项：用于字段的「关联字典」下拉 */
const dictSelectOptions = ref<{ label: string; value: string }[]>([]);

let dictsLoaded = false;

async function ensureDictsLoaded() {
  if (dictsLoaded) return;
  dictsLoaded = true;
  try {
    const res = await DictAPI.list();
    dictSelectOptions.value = res.data.map((d) => ({
      label: `${d.dict_name}（${d.dict_type}）`,
      value: d.dict_type,
    }));
    // 并发加载所有字典项
    await Promise.all(
      res.data.map(async (d) => {
        const r = await DictAPI.listItems(d.dict_type);
        dictMap.value[d.dict_type] = r.data.map((item: DictItem) => ({
          label: item.item_label,
          value: item.item_value,
        }));
      }),
    );
  } catch {
    // 加载失败不影响主流程
  }
}

// ── Schema 抽屉 ───────────────────────────────────────────────────────────────

const schemaVisible    = ref(false);
const schemaSaving     = ref(false);
const schemaCategory   = ref<ArchiveCategory | null>(null);
const schemaFields     = ref<FieldDefinition[]>([]);

/** 继承字段（按 sort_order 升序），直接可编辑 required/default_value */
const inheritedFields = computed(() =>
  schemaFields.value
    .filter((f) => f.inherited)
    .slice()
    .sort((a, b) => (a.sort_order ?? 0) - (b.sort_order ?? 0)),
);

/** 本地可编辑的自定义字段副本 */
const customFieldsLocal = ref<FieldDefinition[]>([]);

watch(schemaFields, () => {
  customFieldsLocal.value = schemaFields.value
    .filter((f) => !f.inherited)
    .map((f) => ({ ...f }));
});

async function openSchemaDrawer(row: ArchiveCategory) {
  schemaCategory.value = row;
  const res = await CategoryAPI.getSchema(row.id);
  schemaFields.value   = res.data ?? [];
  schemaVisible.value  = true;
  await ensureDictsLoaded();
}

function addField() {
  customFieldsLocal.value.push({
    name: "",
    label: "",
    type: "text",
    required: false,
    inherited: false,
    sort_order: customFieldsLocal.value.length + 100,
  });
}

function removeCustomField(idx: number) {
  customFieldsLocal.value.splice(idx, 1);
}

async function saveSchema() {
  if (!schemaCategory.value) return;
  customFieldsLocal.value.forEach((f, i) => { f.sort_order = i + 100; });
  // inheritedFields 已经是 schemaFields 里的对象引用，用户可能编辑了 required/default_value
  const merged = [...inheritedFields.value, ...customFieldsLocal.value];
  schemaSaving.value = true;
  try {
    await CategoryAPI.updateSchema(schemaCategory.value.id, merged);
    message.success("字段已保存");
    schemaVisible.value = false;
    await loadList();
  } finally {
    schemaSaving.value = false;
  }
}

function goToDesigner() {
  if (!schemaCategory.value) return;
  schemaVisible.value = false;
  router.push(`/archive/settings/categories/${schemaCategory.value.id}/form-designer`);
}

function goDesigner(row: ArchiveCategory) {
  router.push(`/archive/settings/categories/${row.id}/form-designer`);
}

// ── 拖拽排序（自定义字段） ────────────────────────────────────────────────────

const dragIdx     = ref<number | null>(null);
const dragOverIdx = ref<number | null>(null);

function onDragStart(idx: number) { dragIdx.value = idx; }
function onDragEnter(idx: number) { dragOverIdx.value = idx; }
function onDragEnd()              { dragIdx.value = null; dragOverIdx.value = null; }

function onDrop(targetIdx: number) {
  const src = dragIdx.value;
  if (src === null || src === targetIdx) return;
  const list    = customFieldsLocal.value;
  const removed = list.splice(src, 1);
  if (!removed[0]) return;
  list.splice(targetIdx, 0, removed[0]);
  dragIdx.value     = null;
  dragOverIdx.value = null;
}

// ── 加载 ──────────────────────────────────────────────────────────────────────

async function loadList() {
  loading.value = true;
  try {
    const res        = await CategoryAPI.list();
    categories.value = res.data;
  } finally {
    loading.value = false;
  }
}

onMounted(loadList);
</script>

