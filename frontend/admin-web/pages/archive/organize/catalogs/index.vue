<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="目录管理"
      description="管理全宗下的整理单元（案卷目录 / 卷内目录 / 一文一件）"
      icon="heroicons:bars-3-bottom-left"
    />

    <!-- 工具栏 -->
    <div class="pro-card p-4 flex flex-wrap items-center gap-3">
      <span class="text-sm font-medium">全宗</span>
      <NSelect
        v-model:value="fondsId"
        :options="fondsOptions"
        placeholder="选择全宗后查看其目录"
        style="width: 280px"
        @update:value="loadCatalogs"
      />
      <NButton tertiary :disabled="!fondsId" @click="loadCatalogs">
        <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
        刷新
      </NButton>
      <div class="flex-1" />
      <NButton type="primary" :disabled="!fondsId" @click="openCreate">
        <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
        新建目录
      </NButton>
    </div>

    <!-- 列表 -->
    <div class="pro-card p-5">
      <ProTable :columns="columns" :data="catalogs" :loading="loading" :page-size="15" size="small" />
    </div>

    <!-- 新建 / 编辑 -->
    <NModal
      v-model:show="showModal"
      preset="card"
      :title="editing ? '编辑目录' : '新建目录'"
      style="width: 560px; max-width: 95vw"
      :mask-closable="false"
    >
      <div class="flex flex-col gap-4">
        <LabeledField label="目录号" required>
          <NInput v-model:value="form.catalog_no" placeholder="如 WS·2024" :disabled="editing" />
        </LabeledField>
        <LabeledField label="目录名称" required>
          <NInput v-model:value="form.name" placeholder="目录名称" />
        </LabeledField>
        <div class="grid grid-cols-2 gap-4">
          <LabeledField label="门类" required>
            <NSelect v-model:value="form.category_id" :options="categoryOptions" placeholder="选择门类" :disabled="editing" />
          </LabeledField>
          <LabeledField label="年度">
            <NInputNumber v-model:value="form.year" :show-button="false" class="w-full" placeholder="年度" />
          </LabeledField>
          <LabeledField label="目录类型" required>
            <NSelect v-model:value="form.catalog_type" :options="typeOptions" />
          </LabeledField>
        </div>
      </div>
      <template #footer>
        <div class="flex justify-end gap-3">
          <NButton @click="showModal = false">取消</NButton>
          <NButton type="primary" :loading="saving" @click="submit">{{ editing ? '保存' : '创建' }}</NButton>
        </div>
      </template>
    </NModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, reactive, computed, onMounted, h } from "vue";
import { NSelect, NInput, NInputNumber, NButton, NModal, NTag, useMessage, useDialog } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { FondsAPI, CategoryAPI, CatalogAPI } from "@/api/repository";
import type { Fonds, ArchiveCategory, Catalog, CatalogType } from "@/api/repository";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();

const typeOptions = [
  { label: "一文一件", value: "一文一件" },
  { label: "案卷目录", value: "案卷目录" },
  { label: "卷内目录", value: "卷内目录" },
];

const LabeledField = (props: { label: string; required?: boolean }, { slots }: { slots: { default?: () => unknown } }) =>
  h("div", { class: "flex flex-col gap-1" }, [
    h("span", { class: "text-sm font-medium" }, [
      props.label,
      props.required ? h("span", { class: "text-red-500 ml-0.5" }, "*") : null,
    ]),
    slots.default?.(),
  ]);

// ── 选项 ──────────────────────────────────────────────────────────
const fondsList = ref<Fonds[]>([]);
const categoryList = ref<ArchiveCategory[]>([]);
const fondsId = ref<string | null>(null);
const fondsOptions = computed(() => fondsList.value.map((f) => ({ label: `${f.fonds_code} - ${f.name}`, value: f.id })));
const categoryOptions = computed(() => categoryList.value.map((c) => ({ label: `${c.code} - ${c.name}`, value: c.id })));

// ── 列表 ──────────────────────────────────────────────────────────
const loading = ref(false);
const catalogs = ref<Catalog[]>([]);

async function loadCatalogs() {
  if (!fondsId.value) { catalogs.value = []; return; }
  loading.value = true;
  try {
    catalogs.value = (await CatalogAPI.list(fondsId.value)).data;
  } finally {
    loading.value = false;
  }
}

const TYPE_TONE: Record<string, "default" | "info" | "warning"> = {
  "一文一件": "default", "案卷目录": "info", "卷内目录": "warning",
};

const columns: DataTableColumns<Catalog> = [
  { title: "目录号", key: "catalog_no", width: 140 },
  { title: "名称", key: "name", ellipsis: { tooltip: true } },
  { title: "年度", key: "year", width: 80 },
  {
    title: "类型", key: "catalog_type", width: 110,
    render: (row) => h(NTag, { size: "small", type: TYPE_TONE[row.catalog_type] ?? "default" }, () => row.catalog_type),
  },
  {
    title: "操作", key: "actions", width: 130,
    render: (row) => h("div", { class: "flex gap-2" }, [
      h(NButton, { size: "small", tertiary: true, onClick: () => openEdit(row) }, () => "编辑"),
      h(NButton, { size: "small", tertiary: true, type: "error", onClick: () => confirmDelete(row) }, () => "删除"),
    ]),
  },
];

// ── 创建 / 编辑 ───────────────────────────────────────────────────
const showModal = ref(false);
const editing = ref(false);
const editingId = ref<string | null>(null);
const saving = ref(false);
const form = reactive({
  catalog_no: "", name: "", category_id: null as string | null,
  year: null as number | null, catalog_type: "一文一件" as CatalogType,
});

function reset() {
  form.catalog_no = ""; form.name = ""; form.category_id = null;
  form.year = null; form.catalog_type = "一文一件";
}

function openCreate() {
  editing.value = false; editingId.value = null; reset();
  showModal.value = true;
}

function openEdit(row: Catalog) {
  editing.value = true; editingId.value = row.id;
  form.catalog_no = row.catalog_no; form.name = row.name;
  form.category_id = row.category_id; form.year = row.year ?? null;
  form.catalog_type = row.catalog_type;
  showModal.value = true;
}

async function submit() {
  if (!form.name.trim() || (!editing.value && (!form.catalog_no.trim() || !form.category_id))) {
    message.warning("请填写目录号、名称与门类");
    return;
  }
  saving.value = true;
  try {
    if (editing.value && editingId.value) {
      await CatalogAPI.update(editingId.value, {
        name: form.name, year: form.year, catalog_type: form.catalog_type,
      });
      message.success("已保存");
    } else {
      await CatalogAPI.create({
        fonds_id: fondsId.value!, category_id: form.category_id!,
        catalog_no: form.catalog_no, name: form.name,
        year: form.year ?? undefined, catalog_type: form.catalog_type,
      });
      message.success("目录已创建");
    }
    showModal.value = false;
    await loadCatalogs();
  } finally {
    saving.value = false;
  }
}

function confirmDelete(row: Catalog) {
  dialog.warning({
    title: "删除目录",
    content: `确认删除目录「${row.name}」？该目录下若已有档案将无法删除。`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await CatalogAPI.remove(row.id);
      message.success("已删除");
      await loadCatalogs();
    },
  });
}

onMounted(async () => {
  const [f, c] = await Promise.all([FondsAPI.list(), CategoryAPI.list()]);
  fondsList.value = f.data;
  categoryList.value = c.data;
});
</script>
