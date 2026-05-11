<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="档案著录"
      description="查询、新增、编辑全宗内的档案条目"
      icon="heroicons:document-text"
    />

    <!-- 筛选栏 -->
    <div class="pro-card p-4 flex flex-wrap gap-3 items-end">
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
        <NInputNumber v-model:value="filter.ND" placeholder="年度" style="width: 100px" :min="1900" :max="2099" />
      </div>
      <div class="flex flex-col gap-1">
        <span class="text-xs text-gray-500">密级</span>
        <NSelect
          v-model:value="filter.MJ"
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
        <NFormItem path="TM" label="题名">
          <NInput v-model:value="formData.TM" placeholder="档案题名（必填）" />
        </NFormItem>
        <NFormItem path="QZH" label="全宗号">
          <NInput v-model:value="formData.QZH" placeholder="如 J001" />
        </NFormItem>
        <div class="grid grid-cols-2 gap-x-4">
          <NFormItem path="RZZ" label="责任者">
            <NInput v-model:value="formData.RZZ" placeholder="可选" />
          </NFormItem>
          <NFormItem path="ND" label="年度">
            <NInputNumber v-model:value="formData.ND" placeholder="年度" class="w-full" />
          </NFormItem>
          <NFormItem path="MJ" label="密级">
            <NSelect v-model:value="formData.MJ" :options="securityOptions" class="w-full" />
          </NFormItem>
          <NFormItem path="BGQX" label="保管期限">
            <NSelect v-model:value="formData.BGQX" :options="retentionOptions" class="w-full" />
          </NFormItem>
          <NFormItem path="WJRQ" label="文件日期">
            <NInput v-model:value="formData.WJRQ" placeholder="YYYY-MM-DD" />
          </NFormItem>
          <NFormItem path="YS" label="页数">
            <NInputNumber v-model:value="formData.YS" placeholder="可选" class="w-full" />
          </NFormItem>
        </div>
        <NFormItem label="档号">
          <NInput v-model:value="formData.DH" placeholder="留空则自动生成（需配置档号规则）" />
        </NFormItem>
      </NForm>
    </CrudModal>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted, reactive } from "vue";
import {
  NButton, NInput, NInputNumber, NSelect, NForm, NFormItem, NTag,
  useMessage, useDialog,
} from "naive-ui";
import type { FormInst } from "naive-ui";
import { FondsAPI, CatalogAPI, CategoryAPI, ArchiveAPI } from "@/api/repository";
import type { Fonds, Catalog, ArchiveCategory, Archive, ArchiveCreate, ArchiveUpdate } from "@/api/repository";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { CrudModal } from "@/components/ui";

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
  { label: "草稿", value: "draft" },
  { label: "待审", value: "pending_review" },
  { label: "退回", value: "rejected" },
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
  draft: "草稿", pending_review: "待审", rejected: "退回",
};

const filter = reactive({
  fonds_id: null as string | null,
  catalog_id: null as string | null,
  category_id: null as string | null,
  ND: null as number | null,
  keyword: "",
  MJ: null as string | null,
  status: null as string | null,
  page: 1,
  page_size: 20,
});

async function onFondsChange(id: string | null) {
  filter.catalog_id = null;
  catalogList.value = [];
  if (id) {
    const res = await CatalogAPI.list(id);
    catalogList.value = res.data;
  }
}

function resetFilter() {
  Object.assign(filter, {
    fonds_id: null, catalog_id: null, category_id: null,
    ND: null, keyword: "", MJ: null, status: null, page: 1,
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

const columns = [
  { title: "档号", key: "DH", width: 140, ellipsis: { tooltip: true } },
  { title: "题名", key: "TM", ellipsis: { tooltip: true } },
  { title: "责任者", key: "RZZ", width: 120, ellipsis: true },
  { title: "年度", key: "ND", width: 70 },
  { title: "全宗号", key: "QZH", width: 90 },
  {
    title: "密级",
    key: "MJ",
    width: 80,
    render: (row: Archive) => (
      <NTag type={securityType[row.MJ] ?? "default"} size="small">
        {securityLabel[row.MJ] ?? row.MJ}
      </NTag>
    ),
  },
  {
    title: "状态",
    key: "status",
    width: 80,
    render: (row: Archive) => <span>{statusLabel[row.status] ?? row.status}</span>,
  },
  {
    title: "操作",
    key: "actions",
    width: 120,
    render: (row: Archive) => (
      <div class="flex items-center gap-1 flex-nowrap">
        <NButton size="small" onClick={() => openModal(row)}>编辑</NButton>
        <NButton size="small" type="error" onClick={() => confirmDelete(row)}>删除</NButton>
      </div>
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
  TM: "",
  QZH: "",
  RZZ: "",
  ND: null as number | null,
  WJRQ: "",
  YS: null as number | null,
  MJ: "public",
  BGQX: "permanent",
  DH: "",
});

const formData = reactive(emptyForm());

const rules = {
  fonds_id: [{ required: true, message: "请选择全宗", trigger: "change" }],
  catalog_id: [{ required: true, message: "请选择目录", trigger: "change" }],
  TM: [{ required: true, message: "请输入题名", trigger: "blur" }],
  QZH: [{ required: true, message: "请输入全宗号", trigger: "blur" }],
};

async function onFormFondsChange(id: string | null) {
  formData.catalog_id = "";
  formCatalogs.value = [];
  if (id) {
    const selectedFonds = fondsList.value.find((f) => f.id === id);
    if (selectedFonds) formData.QZH = selectedFonds.fonds_code;
    const res = await CatalogAPI.list(id);
    formCatalogs.value = res.data;
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
      TM: row.TM,
      QZH: row.QZH,
      RZZ: row.RZZ ?? "",
      ND: row.ND ?? null,
      WJRQ: row.WJRQ ?? "",
      YS: row.YS ?? null,
      MJ: row.MJ,
      BGQX: row.BGQX,
      DH: row.DH ?? "",
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
        TM: formData.TM,
        RZZ: formData.RZZ || undefined,
        ND: formData.ND ?? undefined,
        WJRQ: formData.WJRQ || undefined,
        YS: formData.YS ?? undefined,
        MJ: formData.MJ,
        BGQX: formData.BGQX,
        DH: formData.DH || undefined,
      };
      await ArchiveAPI.update(editId.value, payload);
      message.success("已更新");
    } else {
      const payload: ArchiveCreate = {
        fonds_id: formData.fonds_id,
        catalog_id: formData.catalog_id,
        category_id: formData.category_id!,
        TM: formData.TM,
        QZH: formData.QZH,
        RZZ: formData.RZZ || undefined,
        ND: formData.ND ?? undefined,
        WJRQ: formData.WJRQ || undefined,
        YS: formData.YS ?? undefined,
        MJ: formData.MJ,
        BGQX: formData.BGQX,
        DH: formData.DH || undefined,
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
    content: `确定删除「${row.TM}」？（软删除）`,
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
      ...(filter.ND ? { ND: filter.ND } : {}),
      ...(filter.keyword ? { keyword: filter.keyword } : {}),
      ...(filter.MJ ? { MJ: filter.MJ } : {}),
      ...(filter.status ? { status: filter.status } : {}),
      page: filter.page,
      page_size: filter.page_size,
    };
    const res = await ArchiveAPI.list(params);
    archiveList.value = res.data.items;
    total.value = res.data.total;
  } finally {
    loading.value = false;
  }
}

async function loadRefData() {
  const [fondsRes, catRes] = await Promise.all([FondsAPI.list(), CategoryAPI.list()]);
  fondsList.value = fondsRes.data;
  categoryList.value = catRes.data;
}

onMounted(() => {
  loadRefData();
  loadArchives();
});
</script>
