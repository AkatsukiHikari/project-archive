<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="档案著录"
      description="查询、新增、编辑全宗内的档案条目"
      icon="heroicons:document-text"
    />

    <!-- 筛选栏 -->
    <div class="pro-card flex flex-wrap gap-3 items-end">
      <div class="flex flex-col gap-1">
        <span class="text-xs text-gray-500">全宗</span>
        <NSelect
          v-model:value="filter.fonds_id"
          :options="fondsOptions"
          placeholder="选择全宗"
          style="width: 200px"
          clearable
          @update:value="onFondsChange"
        />
      </div>
      <div class="flex flex-col gap-1">
        <span class="text-xs text-gray-500">目录</span>
        <NSelect
          v-model:value="filter.catalog_id"
          :options="catalogOptions"
          placeholder="选择目录"
          style="width: 200px"
          clearable
          :disabled="!filter.fonds_id"
        />
      </div>
      <div class="flex flex-col gap-1">
        <span class="text-xs text-gray-500">门类</span>
        <NSelect
          v-model:value="filter.category_id"
          :options="categoryOptions"
          placeholder="选择门类"
          style="width: 160px"
          clearable
        />
      </div>
      <div class="flex flex-col gap-1">
        <span class="text-xs text-gray-500">年度</span>
        <NInputNumber v-model:value="filter.year" placeholder="年度" style="width: 100px" :min="1900" :max="2099" />
      </div>
      <div class="flex flex-col gap-1">
        <span class="text-xs text-gray-500">密级</span>
        <NSelect
          v-model:value="filter.security_level"
          :options="securityOptions"
          placeholder="全部"
          style="width: 130px"
          clearable
        />
      </div>
      <div class="flex flex-col gap-1">
        <span class="text-xs text-gray-500">状态</span>
        <NSelect
          v-model:value="filter.status"
          :options="statusOptions"
          placeholder="全部"
          style="width: 110px"
          clearable
        />
      </div>
      <div class="flex flex-col gap-1">
        <span class="text-xs text-gray-500">关键字</span>
        <NInput v-model:value="filter.keyword" placeholder="题名/责任者" style="width: 180px" clearable />
      </div>
      <NButton type="primary" @click="search">查询</NButton>
      <NButton @click="resetFilter">重置</NButton>
      <div class="ml-auto">
        <NButton type="primary" :disabled="!filter.fonds_id" @click="openModal(null)">
          <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
          新增档案
        </NButton>
      </div>
    </div>

    <ProTable
      :columns="columns"
      :data="archiveList"
      :loading="loading"
      empty-content="暂无档案数据"
      :total="total"
      :current-page="filter.page"
      :page-size="filter.page_size"
      :remote="true"
      @page-change="onPageChange"
    />

    <CrudModal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑档案' : '新增档案'"
      :loading="saving"
      :width="600"
      @confirm="submitForm"
    >
      <NForm ref="formRef" :model="formData" :rules="rules" label-placement="left" :label-width="90">
        <NFormItem path="fonds_id" label="全宗">
          <NSelect v-model:value="formData.fonds_id" :options="fondsOptions" :disabled="isEdit" placeholder="选择全宗" @update:value="onFormFondsChange" />
        </NFormItem>
        <NFormItem path="catalog_id" label="目录">
          <NSelect v-model:value="formData.catalog_id" :options="formCatalogOptions" placeholder="选择目录" :disabled="!formData.fonds_id || isEdit" />
        </NFormItem>
        <NFormItem path="category_id" label="门类">
          <NSelect v-model:value="formData.category_id" :options="categoryOptions" placeholder="选择门类" />
        </NFormItem>
        <NFormItem path="title" label="题名">
          <NInput v-model:value="formData.title" placeholder="档案题名（必填）" />
        </NFormItem>
        <NFormItem path="fonds_code" label="全宗号">
          <NInput v-model:value="formData.fonds_code" placeholder="如 J001" />
        </NFormItem>
        <div class="grid grid-cols-2 gap-x-4">
          <NFormItem path="creator" label="责任者">
            <NInput v-model:value="formData.creator" placeholder="可选" />
          </NFormItem>
          <NFormItem path="year" label="年度">
            <NInputNumber v-model:value="formData.year" placeholder="年度" class="w-full" />
          </NFormItem>
          <NFormItem path="security_level" label="密级">
            <NSelect v-model:value="formData.security_level" :options="securityOptions" class="w-full" />
          </NFormItem>
          <NFormItem path="retention_period" label="保管期限">
            <NSelect v-model:value="formData.retention_period" :options="retentionOptions" class="w-full" />
          </NFormItem>
          <NFormItem path="doc_date" label="文件日期">
            <NInput v-model:value="formData.doc_date" placeholder="YYYY-MM-DD" />
          </NFormItem>
          <NFormItem path="pages" label="页数">
            <NInputNumber v-model:value="formData.pages" placeholder="可选" class="w-full" />
          </NFormItem>
        </div>
        <NFormItem label="档号">
          <NInput v-model:value="formData.archive_no" placeholder="留空则自动生成（需配置档号规则）" />
        </NFormItem>
      </NForm>
    </CrudModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted, reactive } from "vue";
import {
  NButton, NInput, NInputNumber, NSelect, NForm, NFormItem, NTag, NSpace,
  useMessage, useDialog,
} from "naive-ui";
import type { FormInst, DataTableColumns } from "naive-ui";
import { FondsAPI, CatalogAPI, CategoryAPI, ArchiveAPI } from "@/api/repository";
import type { Fonds, Catalog, ArchiveCategory, Archive, ArchiveCreate, ArchiveUpdate } from "@/api/repository";
import AdminPageHeader from "@/components/admin/PageHeader.vue";
import ProTable from "@/components/ui/ProTable.vue";
import CrudModal from "@/components/ui/CrudModal.vue";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();

const fondsList = ref<Fonds[]>([]);
const catalogList = ref<Catalog[]>([]);
const categoryList = ref<ArchiveCategory[]>([]);
const formCatalogs = ref<Catalog[]>([]);

const fondsOptions = computed(() =>
  fondsList.value.map((f) => ({ label: `${f.fonds_code} - ${f.name}`, value: f.id })),
);
const catalogOptions = computed(() =>
  catalogList.value.map((c) => ({ label: `${c.catalog_no} ${c.name}`, value: c.id })),
);
const formCatalogOptions = computed(() =>
  formCatalogs.value.map((c) => ({ label: `${c.catalog_no} ${c.name}`, value: c.id })),
);
const categoryOptions = computed(() =>
  categoryList.value.map((c) => ({ label: `${c.code} - ${c.name}`, value: c.id })),
);

const securityOptions = [
  { label: "公开", value: "public" },
  { label: "内部", value: "internal" },
  { label: "机密", value: "confidential" },
  { label: "秘密", value: "secret" },
];
const statusOptions = [
  { label: "在用", value: "active" },
  { label: "受限", value: "restricted" },
  { label: "销毁", value: "destroyed" },
];
const retentionOptions = [
  { label: "永久", value: "permanent" },
  { label: "长期", value: "long" },
  { label: "短期", value: "short" },
];

const securityLabel: Record<string, string> = {
  public: "公开", internal: "内部", confidential: "机密", secret: "秘密",
};
const securityType: Record<string, "default" | "info" | "warning" | "error"> = {
  public: "default", internal: "info", confidential: "warning", secret: "error",
};
const statusLabel: Record<string, string> = {
  active: "在用", restricted: "受限", destroyed: "销毁",
};

const filter = reactive({
  fonds_id: null as string | null,
  catalog_id: null as string | null,
  category_id: null as string | null,
  year: null as number | null,
  keyword: "",
  security_level: null as string | null,
  status: null as string | null,
  page: 1,
  page_size: 20,
});

async function onFondsChange(id: string | null) {
  filter.catalog_id = null;
  catalogList.value = [];
  if (id) {
    const res = await CatalogAPI.list(id);
    catalogList.value = res.data.data;
  }
}

function resetFilter() {
  Object.assign(filter, {
    fonds_id: null, catalog_id: null, category_id: null,
    year: null, keyword: "", security_level: null, status: null, page: 1,
  });
  catalogList.value = [];
  loadArchives();
}

function search() {
  filter.page = 1;
  loadArchives();
}

function onPageChange(page: number, pageSize: number) {
  filter.page = page;
  filter.page_size = pageSize;
  loadArchives();
}

const archiveList = ref<Archive[]>([]);
const total = ref(0);
const loading = ref(false);

const columns: DataTableColumns<Archive> = [
  { title: "档号", key: "archive_no", width: 140, ellipsis: { tooltip: true } },
  { title: "题名", key: "title", ellipsis: { tooltip: true } },
  { title: "责任者", key: "creator", width: 120, ellipsis: true },
  { title: "年度", key: "year", width: 70 },
  { title: "全宗号", key: "fonds_code", width: 90 },
  {
    title: "密级",
    key: "security_level",
    width: 80,
    render: (row) => (
      <NTag type={securityType[row.security_level] ?? "default"} size="small">
        {securityLabel[row.security_level] ?? row.security_level}
      </NTag>
    ),
  },
  {
    title: "状态",
    key: "status",
    width: 80,
    render: (row) => <span>{statusLabel[row.status] ?? row.status}</span>,
  },
  {
    title: "操作",
    key: "actions",
    width: 140,
    render: (row) => (
      <NSpace size="small">
        <NButton size="small" onClick={() => openModal(row)}>编辑</NButton>
        <NButton size="small" type="error" onClick={() => confirmDelete(row)}>删除</NButton>
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
  fonds_id: filter.fonds_id ?? "",
  catalog_id: filter.catalog_id ?? "",
  category_id: null as string | null,
  title: "",
  fonds_code: "",
  creator: "",
  year: null as number | null,
  doc_date: "",
  pages: null as number | null,
  security_level: "public",
  retention_period: "permanent",
  archive_no: "",
});

const formData = reactive(emptyForm());

const rules = {
  fonds_id: [{ required: true, message: "请选择全宗", trigger: "change" }],
  catalog_id: [{ required: true, message: "请选择目录", trigger: "change" }],
  title: [{ required: true, message: "请输入题名", trigger: "blur" }],
  fonds_code: [{ required: true, message: "请输入全宗号", trigger: "blur" }],
};

async function onFormFondsChange(id: string | null) {
  formData.catalog_id = "";
  formCatalogs.value = [];
  if (id) {
    const selectedFonds = fondsList.value.find((f) => f.id === id);
    if (selectedFonds) formData.fonds_code = selectedFonds.fonds_code;
    const res = await CatalogAPI.list(id);
    formCatalogs.value = res.data.data;
  }
}

function openModal(row: Archive | null) {
  if (row) {
    isEdit.value = true;
    editId.value = row.id;
    Object.assign(formData, {
      fonds_id: row.fonds_id,
      catalog_id: row.catalog_id,
      category_id: row.category_id,
      title: row.title,
      fonds_code: row.fonds_code,
      creator: row.creator ?? "",
      year: row.year ?? null,
      doc_date: row.doc_date ?? "",
      pages: row.pages ?? null,
      security_level: row.security_level,
      retention_period: row.retention_period,
      archive_no: row.archive_no ?? "",
    });
  } else {
    isEdit.value = false;
    editId.value = null;
    Object.assign(formData, emptyForm());
    if (filter.fonds_id) {
      formData.fonds_id = filter.fonds_id;
      onFormFondsChange(filter.fonds_id);
    }
    if (filter.catalog_id) formData.catalog_id = filter.catalog_id;
  }
  modalVisible.value = true;
}

async function submitForm() {
  await formRef.value?.validate();
  saving.value = true;
  try {
    if (isEdit.value && editId.value) {
      const payload: ArchiveUpdate = {
        title: formData.title,
        creator: formData.creator || undefined,
        year: formData.year ?? undefined,
        doc_date: formData.doc_date || undefined,
        pages: formData.pages ?? undefined,
        security_level: formData.security_level,
        retention_period: formData.retention_period,
        archive_no: formData.archive_no || undefined,
      };
      await ArchiveAPI.update(editId.value, payload);
      message.success("已更新");
    } else {
      const payload: ArchiveCreate = {
        fonds_id: formData.fonds_id,
        catalog_id: formData.catalog_id,
        category_id: formData.category_id!,
        title: formData.title,
        fonds_code: formData.fonds_code,
        creator: formData.creator || undefined,
        year: formData.year ?? undefined,
        doc_date: formData.doc_date || undefined,
        pages: formData.pages ?? undefined,
        security_level: formData.security_level,
        retention_period: formData.retention_period,
        archive_no: formData.archive_no || undefined,
      };
      await ArchiveAPI.create(payload);
      message.success("已创建");
    }
    modalVisible.value = false;
    await loadArchives();
  } finally {
    saving.value = false;
  }
}

function confirmDelete(row: Archive) {
  dialog.warning({
    title: "删除确认",
    content: `确定删除「${row.title}」？（软删除）`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await ArchiveAPI.remove(row.id);
      message.success("已删除");
      await loadArchives();
    },
  });
}

async function loadArchives() {
  loading.value = true;
  try {
    const params = {
      ...(filter.fonds_id ? { fonds_id: filter.fonds_id } : {}),
      ...(filter.catalog_id ? { catalog_id: filter.catalog_id } : {}),
      ...(filter.category_id ? { category_id: filter.category_id } : {}),
      ...(filter.year ? { year: filter.year } : {}),
      ...(filter.keyword ? { keyword: filter.keyword } : {}),
      ...(filter.security_level ? { security_level: filter.security_level } : {}),
      ...(filter.status ? { status: filter.status } : {}),
      page: filter.page,
      page_size: filter.page_size,
    };
    const res = await ArchiveAPI.list(params);
    archiveList.value = res.data.data.items;
    total.value = res.data.data.total;
  } finally {
    loading.value = false;
  }
}

async function loadRefData() {
  const [fondsRes, catRes] = await Promise.all([FondsAPI.list(), CategoryAPI.list()]);
  fondsList.value = fondsRes.data.data;
  categoryList.value = catRes.data.data;
}

onMounted(() => {
  loadRefData();
  loadArchives();
});
</script>
