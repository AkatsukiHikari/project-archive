<template>
  <div class="flex flex-col gap-3 min-h-0 flex-1">
    <AdminPageHeader
      title="档案著录 / 整理"
      description="对暂存库档案进行著录、批量修改、重编档号、挂接数字化成果，整理完成后归档入库"
      icon="heroicons:pencil-square"
    />

    <!-- ── 组合检索区（与查阅登记同风格） ─────────────────── -->
    <div class="pro-card p-4 flex flex-col gap-3">
      <div class="flex flex-wrap items-center gap-3">
        <NInput
          v-model:value="filter.keyword"
          placeholder="题名 / 责任者 / 档号"
          clearable
          style="width: 320px"
          @keydown.enter="search"
        >
          <template #prefix><Icon name="heroicons:magnifying-glass" class="w-4 h-4 text-gray-400" /></template>
        </NInput>
        <NButton type="primary" :loading="loading" @click="search">查询</NButton>
        <NButton tertiary @click="resetFilter">重置</NButton>
        <NButton text type="primary" @click="advanced = !advanced">
          <Icon :name="advanced ? 'heroicons:chevron-up' : 'heroicons:adjustments-horizontal'" class="w-4 h-4 mr-1" />
          {{ advanced ? "收起" : "高级查询" }}
        </NButton>
        <div class="flex-1" />
        <span class="text-sm text-gray-500">共 <strong>{{ total }}</strong> 条</span>
      </div>

      <div
        v-show="advanced"
        class="grid grid-cols-2 lg:grid-cols-4 gap-x-4 gap-y-3 pt-1 border-t"
        style="border-color: var(--semi-color-border)"
      >
        <Field label="题名"><NInput v-model:value="filter.TM" placeholder="题名关键字" clearable /></Field>
        <Field label="责任者"><NInput v-model:value="filter.RZZ" placeholder="责任者" clearable /></Field>
        <Field label="档号"><NInput v-model:value="filter.DH" placeholder="档号" clearable /></Field>
        <Field label="全宗">
          <NSelect v-model:value="filter.fonds_id" :options="fondsOptions" placeholder="全部全宗" clearable filterable @update:value="onFondsChange" />
        </Field>
        <Field label="目录">
          <NSelect v-model:value="filter.catalog_id" :options="catalogOptions" placeholder="全部目录" clearable :disabled="!filter.fonds_id" />
        </Field>
        <Field label="门类">
          <NSelect v-model:value="filter.category_id" :options="categoryOptions" placeholder="全部门类" clearable filterable />
        </Field>
        <Field label="密级"><NSelect v-model:value="filter.MJ" :options="mjOptions" placeholder="全部" clearable /></Field>
        <Field label="保管期限"><NSelect v-model:value="filter.BGQX" :options="bgqxOptions" placeholder="全部" clearable /></Field>
        <Field label="整理状态"><NSelect v-model:value="filter.status" :options="statusOptions" placeholder="全部" clearable /></Field>
        <Field label="年度">
          <div class="flex items-center gap-1">
            <NInputNumber v-model:value="filter.ND_from" :show-button="false" placeholder="起" class="flex-1" />
            <span class="text-gray-400">~</span>
            <NInputNumber v-model:value="filter.ND_to" :show-button="false" placeholder="止" class="flex-1" />
          </div>
        </Field>
        <Field label="文件日期">
          <div class="flex items-center gap-1">
            <NInput v-model:value="filter.WJRQ_from" placeholder="2020-01-01" clearable class="flex-1" />
            <span class="text-gray-400">~</span>
            <NInput v-model:value="filter.WJRQ_to" placeholder="2025-12-31" clearable class="flex-1" />
          </div>
        </Field>
      </div>
    </div>

    <!-- ── 目录导航 + 结果表 ─────────────────────────────── -->
    <div class="flex gap-3 flex-1 min-h-0">
      <CatalogNavTree @select="onNavScope" @clear="clearNavScope" />
      <div class="pro-card p-4 flex-1 min-w-0 min-h-0 flex flex-col gap-3">
      <!-- 整理工具条 -->
      <div class="flex flex-wrap items-center gap-2">
        <NButton size="small" type="primary" @click="openModal(null)">
          <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
          新增著录
        </NButton>
        <NButton size="small" @click="showAttachWizard = true">
          <template #icon><Icon name="heroicons:paper-clip" class="w-4 h-4" /></template>
          挂接成果
        </NButton>
        <NButton size="small" :disabled="selectedIds.length === 0 && total === 0" @click="showRenumber = true">
          <template #icon><Icon name="heroicons:hashtag" class="w-4 h-4" /></template>
          重编档号
        </NButton>

        <template v-if="selectedIds.length > 0">
          <span class="w-px h-4" style="background:var(--semi-color-border)" />
          <span class="text-sm" style="color:oklch(var(--p))">已选 <strong>{{ selectedIds.length }}</strong> 条</span>
          <NButton size="small" @click="showBatchEdit = true">
            <template #icon><Icon name="heroicons:pencil-square" class="w-4 h-4" /></template>
            批量修改
          </NButton>
          <NButton size="small" type="primary" secondary @click="confirmArchiveToFormal">
            <template #icon><Icon name="heroicons:archive-box-arrow-down" class="w-4 h-4" /></template>
            归档入库
          </NButton>
          <NButton size="small" type="error" secondary @click="confirmBatchDelete">
            <template #icon><Icon name="heroicons:trash" class="w-4 h-4" /></template>
            批量删除
          </NButton>
          <NButton size="small" quaternary @click="selectedIds = []">取消选择</NButton>
        </template>
      </div>

      <ProTable :columns="columns" :data="archiveList" :loading="loading" :page-size="0" size="small" />

      <div class="flex justify-end">
        <NPagination
          v-model:page="filter.page"
          v-model:page-size="filter.page_size"
          :item-count="total"
          :page-sizes="[20, 50, 100]"
          show-size-picker
          show-quick-jumper
          @update:page="loadArchives"
          @update:page-size="loadArchives"
        />
      </div>
      </div>
    </div>

    <!-- ── 详情抽屉 ───────────────────────────────────────── -->
    <NDrawer v-model:show="detailVisible" :width="560" placement="right">
      <NDrawerContent v-if="detailRow" :title="`档案详情 · ${detailRow.DH || detailRow.TM}`" closable>
        <div class="flex flex-col gap-4">
          <table class="w-full text-[13px] border-collapse">
            <tbody>
              <tr
                v-for="f in detailFields"
                :key="f.label"
                class="border-b"
                style="border-color: var(--semi-color-border)"
              >
                <th class="text-left align-top py-2 pr-3 font-medium whitespace-nowrap" style="width:96px;color:var(--semi-color-text-3)">{{ f.label }}</th>
                <td class="py-2 break-words" :class="f.mono ? 'font-mono' : ''" style="color:var(--semi-color-text-0)">{{ f.value || "—" }}</td>
              </tr>
            </tbody>
          </table>

          <AttachmentPanel :archive-id="detailRow.id" @changed="loadArchives" />
        </div>
        <template #footer>
          <div class="flex w-full items-center gap-2">
            <NButton type="primary" @click="() => { openModal(detailRow!); detailVisible = false; }">
              <template #icon><Icon name="heroicons:pencil-square" class="w-4 h-4" /></template>
              编辑
            </NButton>
            <NButton type="error" ghost @click="() => confirmDelete(detailRow!)">删除</NButton>
            <div class="flex-1" />
            <NButton text type="primary" @click="askAI(detailRow)">
              <template #icon><Icon name="heroicons:sparkles" class="w-4 h-4" /></template>
              让 AI 解读
            </NButton>
          </div>
        </template>
      </NDrawerContent>
    </NDrawer>

    <!-- ── 单条挂接抽屉 ───────────────────────────────────── -->
    <NDrawer v-model:show="attachVisible" :width="480" placement="right">
      <NDrawerContent v-if="attachRow" :title="`挂接数字化成果 · ${attachRow.DH || attachRow.TM}`" closable>
        <div class="flex flex-col gap-3">
          <p class="text-[12.5px] m-0" style="color:var(--semi-color-text-2)">{{ attachRow.TM }}</p>
          <AttachmentPanel :archive-id="attachRow.id" @changed="loadArchives" />
        </div>
      </NDrawerContent>
    </NDrawer>

    <!-- 新增 / 编辑 -->
    <CrudModal
      v-model:visible="modalVisible"
      :title="isEdit ? '编辑档案' : '新增著录'"
      :loading="saving"
      :width="900"
      @confirm="submitForm"
    >
      <NForm ref="formRef" :model="formData" :rules="rules" label-placement="top">
        <div class="grid grid-cols-3 gap-x-4">
          <NFormItem path="fonds_id" label="全宗">
            <NSelect v-model:value="formData.fonds_id" :options="fondsOptions" :disabled="isEdit" placeholder="选择全宗" filterable @update:value="onFormFondsChange" />
          </NFormItem>
          <NFormItem path="catalog_id" label="目录">
            <NSelect v-model:value="formData.catalog_id" :options="formCatalogOptions" placeholder="选择目录" :disabled="!formData.fonds_id || isEdit" />
          </NFormItem>
          <NFormItem path="category_id" label="门类">
            <NSelect v-model:value="formData.category_id" :options="categoryOptions" placeholder="选择门类" filterable @update:value="onFormCategoryChange" />
          </NFormItem>
        </div>
      </NForm>
      <!-- 按所选门类的字段定义 + 排版设计 渲染著录字段 -->
      <div class="pt-3 mt-1 border-t" style="border-color: var(--semi-color-border)">
        <ArchiveDynamicForm ref="dynFormRef" :category-id="formData.category_id" :model="formModel" />
      </div>
    </CrudModal>

    <!-- 整理工具 -->
    <BatchAttachWizard v-model:show="showAttachWizard" @done="loadArchives" />
    <RenumberWizard
      v-model:show="showRenumber"
      :selected-ids="selectedIds"
      :query="currentQuery"
      :query-total="total"
      @done="onOrganizeDone"
    />
    <BatchEditModal
      v-model:show="showBatchEdit"
      :selected-ids="selectedIds"
      @done="onOrganizeDone"
    />

    <ArchiveInterpretDrawer v-model:show="interpretShow" :archive-id="interpretId" :title="interpretTitle" />
  </div>
</template>

<script setup lang="tsx">
import { computed, h, onMounted, reactive, ref } from "vue";
import { useRoute } from "vue-router";
import {
  NButton, NCheckbox, NDrawer, NDrawerContent, NForm, NFormItem, NInput,
  NInputNumber, NPagination, NSelect, NTag,
  useDialog, useMessage,
} from "naive-ui";
import type { DataTableColumns, FormInst } from "naive-ui";
import { ArchiveAPI, CatalogAPI, CategoryAPI, FondsAPI, OrganizeAPI } from "@/api/repository";
import type {
  Archive, ArchiveCategory, ArchiveCreate, ArchiveListParams, ArchiveUpdate, Catalog, Fonds,
} from "@/api/repository";
import { AdminPageHeader } from "@/components/admin";
import { CrudModal, ProTable } from "@/components/ui";
import {
  ArchiveDynamicForm, ArchiveInterpretDrawer, AttachmentPanel, BatchAttachWizard, BatchEditModal, CatalogNavTree, KfztTag, RenumberWizard,
} from "@/components/archive";
import { AppraisalAPI } from "@/api/appraisal";
import type { ArchiveConclusion } from "@/api/appraisal";

definePageMeta({ layout: "archive", middleware: "auth" });

const message = useMessage();
const dialog = useDialog();
const route = useRoute();

type SlotsCtx = { slots: { default?: () => unknown } };
const Field = (props: { label: string }, { slots }: SlotsCtx) =>
  h("div", { class: "flex flex-col gap-1" }, [
    h("span", { class: "text-[11.5px]", style: "color:var(--semi-color-text-3)" }, props.label),
    slots.default?.(),
  ]);

// ── 选项 ─────────────────────────────────────────────────────────────────────
const mjOptions = [
  { label: "无", value: "无" }, { label: "秘密", value: "秘密" },
  { label: "机密", value: "机密" }, { label: "绝密", value: "绝密" },
];
const bgqxOptions = [
  { label: "永久", value: "permanent" }, { label: "长期", value: "long" }, { label: "短期", value: "short" },
];
const statusOptions = [
  { label: "草稿", value: "draft" }, { label: "待审", value: "pending_review" }, { label: "退回", value: "rejected" },
];
// 密级历史英文值兜底映射
const securityLabel: Record<string, string> = {
  "无": "无", "秘密": "秘密", "机密": "机密", "绝密": "绝密",
  public: "无", internal: "无", secret: "秘密", confidential: "机密",
};
const securityType: Record<string, "default" | "info" | "warning" | "error" | "success"> = {
  "无": "default", "秘密": "info", "机密": "warning", "绝密": "error",
  public: "default", internal: "default", secret: "info", confidential: "warning",
};
const retentionLabel: Record<string, string> = { permanent: "永久", long: "长期", short: "短期" };
const statusLabel: Record<string, string> = {
  draft: "草稿", pending_review: "待审", rejected: "退回", archived: "已归档",
};

// ── 引用数据 ─────────────────────────────────────────────────────────────────
const fondsList = ref<Fonds[]>([]);
const catalogList = ref<Catalog[]>([]);
const categoryList = ref<ArchiveCategory[]>([]);
const formCatalogs = ref<Catalog[]>([]);

const fondsOptions = computed(() =>
  fondsList.value.map((f) => ({ label: `${f.fonds_code} - ${f.short_name || f.name}`, value: f.id })),
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
const categoryNameById = computed<Record<string, string>>(() =>
  Object.fromEntries(categoryList.value.map((c) => [c.id, `${c.code} - ${c.name}`])),
);
// 门类扩展字段 拼音码 → 中文标签
const extLabel = computed<Record<string, string>>(() => {
  const m: Record<string, string> = {};
  for (const cat of categoryList.value) {
    for (const fld of cat.field_schema ?? []) {
      if (fld.name && fld.label) m[fld.name] = fld.label;
    }
  }
  return m;
});

// ── 查询状态 ─────────────────────────────────────────────────────────────────
const advanced = ref(false);
const emptyFilter = () => ({
  keyword: "", TM: "", RZZ: "", DH: "",
  fonds_id: null as string | null,
  catalog_id: null as string | null,
  category_id: null as string | null,
  MJ: null as string | null,
  BGQX: null as string | null,
  status: null as string | null,
  ND_from: null as number | null,
  ND_to: null as number | null,
  WJRQ_from: "", WJRQ_to: "",
  page: 1, page_size: 20,
});
const filter = reactive(emptyFilter());

const archiveList = ref<Archive[]>([]);
const total = ref(0);
const loading = ref(false);

const currentQuery = computed<Partial<ArchiveListParams>>(() => ({
  keyword: filter.keyword || undefined,
  TM: filter.TM || undefined,
  RZZ: filter.RZZ || undefined,
  DH: filter.DH || undefined,
  fonds_id: filter.fonds_id ?? undefined,
  catalog_id: filter.catalog_id ?? undefined,
  category_id: filter.category_id ?? undefined,
  MJ: filter.MJ ?? undefined,
  BGQX: filter.BGQX ?? undefined,
  status: filter.status ?? undefined,
  ND_from: filter.ND_from ?? undefined,
  ND_to: filter.ND_to ?? undefined,
  WJRQ_from: filter.WJRQ_from || undefined,
  WJRQ_to: filter.WJRQ_to || undefined,
}));

// 目录导航(门类/全宗/年度)→ 设过滤条件并重查
function onNavScope(scope: { category_id?: string; fonds_id?: string; ND_from?: number; ND_to?: number }) {
  filter.category_id = scope.category_id ?? null;
  filter.fonds_id = scope.fonds_id ?? null;
  filter.ND_from = scope.ND_from ?? null;
  filter.ND_to = scope.ND_to ?? null;
  filter.page = 1;
  loadArchives();
}
function clearNavScope() {
  filter.category_id = null;
  filter.fonds_id = null;
  filter.ND_from = null;
  filter.ND_to = null;
  filter.page = 1;
  loadArchives();
}

async function loadArchives() {
  loading.value = true;
  try {
    const res = await ArchiveAPI.list({
      ...currentQuery.value,
      page: filter.page,
      page_size: filter.page_size,
    });
    archiveList.value = res.data.items as Archive[];
    total.value = res.data.total;
  } finally {
    loading.value = false;
  }
}

function search() {
  filter.page = 1;
  loadArchives();
}

function resetFilter() {
  Object.assign(filter, emptyFilter());
  loadArchives();
}

async function onFondsChange(id: string | null) {
  filter.catalog_id = null;
  catalogList.value = id ? (await CatalogAPI.list(id)).data : [];
}

// ── 勾选 ─────────────────────────────────────────────────────────────────────
const selectedIds = ref<string[]>([]);

const allPageChecked = computed(
  () => archiveList.value.length > 0 && archiveList.value.every((a) => selectedIds.value.includes(a.id)),
);
const somePageChecked = computed(() => archiveList.value.some((a) => selectedIds.value.includes(a.id)));

function toggleSelect(id: string, checked: boolean) {
  selectedIds.value = checked
    ? [...selectedIds.value, id]
    : selectedIds.value.filter((x) => x !== id);
}

function toggleAllPage(checked: boolean) {
  const pageIds = archiveList.value.map((a) => a.id);
  selectedIds.value = checked
    ? [...new Set([...selectedIds.value, ...pageIds])]
    : selectedIds.value.filter((x) => !pageIds.includes(x));
}

// ── 表格 ─────────────────────────────────────────────────────────────────────
const columns = computed<DataTableColumns<Archive>>(() => [
  {
    key: "selection", width: 42,
    title: () => h(NCheckbox, {
      checked: allPageChecked.value,
      indeterminate: somePageChecked.value && !allPageChecked.value,
      "onUpdate:checked": toggleAllPage,
    }),
    render: (r) => h(NCheckbox, {
      checked: selectedIds.value.includes(r.id),
      "onUpdate:checked": (v: boolean) => toggleSelect(r.id, v),
    }),
  },
  {
    title: "档号", key: "DH", width: 190, ellipsis: { tooltip: true },
    render: (r) => h("code", { class: "font-mono text-[12px]" }, r.DH || "—"),
  },
  { title: "题名", key: "TM", minWidth: 220, ellipsis: { tooltip: true } },
  { title: "责任者", key: "RZZ", width: 110, ellipsis: { tooltip: true }, render: (r) => r.RZZ || "—" },
  { title: "年度", key: "ND", width: 64, render: (r) => r.ND ?? "—" },
  {
    title: "密级", key: "MJ", width: 72,
    render: (r) => h(NTag, { size: "small", type: securityType[r.MJ] ?? "default", bordered: false },
      { default: () => securityLabel[r.MJ] ?? r.MJ }),
  },
  { title: "期限", key: "BGQX", width: 60, render: (r) => retentionLabel[r.BGQX] ?? r.BGQX },
  {
    title: "开放状态", key: "KFZT", width: 90,
    render: (r) => h(KfztTag, { value: r.KFZT }),
  },
  {
    title: "原文", key: "attachment_count", width: 70,
    render: (r) => (r.attachment_count
      ? h(NButton, { size: "tiny", text: true, type: "primary", onClick: () => openViewer(r) },
          { default: () => `${r.attachment_count} 份` })
      : h("span", { class: "text-[11.5px]", style: "color:var(--semi-color-text-3)" }, "无")),
  },
  {
    title: "状态", key: "status", width: 70,
    render: (r) => h("span", { class: "text-[12px]" }, statusLabel[r.status] ?? r.status),
  },
  {
    title: "操作", key: "actions", width: 264, fixed: "right" as const,
    render: (r) => [
      h(NButton, { size: "tiny", tertiary: true, class: "mr-1", onClick: () => openDetail(r) }, { default: () => "详情" }),
      h(NButton, { size: "tiny", tertiary: true, type: "primary", class: "mr-1", onClick: () => openAttach(r) }, { default: () => "挂接" }),
      h(NButton, {
        size: "tiny", tertiary: true, type: "primary", class: "mr-1",
        disabled: !r.attachment_count,
        title: r.attachment_count ? "查看原文" : "该档案暂无数字化原文",
        onClick: () => openViewer(r),
      }, { default: () => "查看原文" }),
      h(NButton, { size: "tiny", tertiary: true, type: "error", onClick: () => confirmDelete(r) }, { default: () => "删除" }),
    ],
  },
]);

// ── 详情 / 挂接抽屉 ──────────────────────────────────────────────────────────
const detailVisible = ref(false);
const detailRow = ref<Archive | null>(null);
const conclusion = ref<ArchiveConclusion | null>(null);
const attachVisible = ref(false);
const attachRow = ref<Archive | null>(null);

const detailFields = computed(() => {
  const r = detailRow.value;
  if (!r) return [];
  const base = [
    { label: "档号", value: r.DH, mono: true },
    { label: "题名", value: r.TM },
    { label: "全宗号", value: r.QZH },
    { label: "责任者", value: r.RZZ },
    { label: "年度", value: r.ND ? String(r.ND) : "" },
    { label: "文件日期", value: r.WJRQ },
    { label: "页数", value: r.YS ? String(r.YS) : "" },
    { label: "密级", value: securityLabel[r.MJ] ?? r.MJ },
    { label: "保管期限", value: retentionLabel[r.BGQX] ?? r.BGQX },
    { label: "开放状态", value: r.KFZT ?? "未鉴定" },
    ...(conclusion.value ? [
      { label: "鉴定日期", value: conclusion.value.appraised_at ?? "" },
      { label: "开放理由", value: conclusion.value.reason ?? "" },
      { label: "引用标准", value: conclusion.value.standard_code ?? "" },
    ] : []),
    { label: "门类", value: categoryNameById.value[r.category_id] },
    { label: "整理状态", value: statusLabel[r.status] ?? r.status },
  ];
  // 门类扩展字段全部展开显示（拼音码 → 中文标签）
  const ext = Object.entries(r.ext_fields ?? {}).map(([k, v]) => ({
    label: extLabel.value[k] ?? k,
    value: v == null ? "" : String(v),
    mono: false,
  }));
  return [...base, ...ext];
});

async function openDetail(row: Archive) {
  detailRow.value = row;
  conclusion.value = null;
  detailVisible.value = true;
  if (row.KFZT) {
    const res = await AppraisalAPI.archiveConclusion(row.id);
    if (res.code === 0) conclusion.value = res.data;
  }
}

function openAttach(row: Archive) {
  attachRow.value = row;
  attachVisible.value = true;
}

// ── 查看原文：统一跳转 reader 页（与档案查询一致）──────────────────────────────
const router = useRouter();
function openViewer(row: Archive) {
  router.push(`/archive/reader?id=${row.id}`);
}

const interpretShow = ref(false);
const interpretId = ref<string | null>(null);
const interpretTitle = ref("");
function askAI(row: Archive | null) {
  if (!row) return;
  interpretId.value = row.id;
  interpretTitle.value = `${row.DH || ""} ${row.TM || ""}`.trim();
  interpretShow.value = true;
}

// ── 新增 / 编辑 ──────────────────────────────────────────────────────────────
const modalVisible = ref(false);
const isEdit = ref(false);
const editId = ref<string | null>(null);
const saving = ref(false);
const formRef = ref<FormInst | null>(null);

// 结构字段（决定加载哪套门类 schema，本身不在 field_schema 里）
const emptyForm = () => ({
  fonds_id: null as string | null,
  catalog_id: null as string | null,
  category_id: null as string | null,
});
const formData = reactive(emptyForm());

// 著录字段扁平模型（题名/全宗号/…/门类私有字段），交给 ArchiveDynamicForm 渲染+回写
const formModel = ref<Record<string, unknown>>({});
const dynFormRef = ref<{ validate: () => string[]; fieldNames: () => string[] } | null>(null);

// 著录字段里映射到档案表列的 base 字段，其余进 ext_fields
const BASE_COLUMNS = ["TM", "QZH", "RZZ", "ND", "MJ", "BGQX", "WJRQ", "YS", "DH"];

const rules = {
  fonds_id: { required: true, message: "请选择全宗", trigger: ["change", "blur"] },
  catalog_id: { required: true, message: "请选择目录", trigger: ["change", "blur"] },
  category_id: { required: true, message: "请选择门类", trigger: ["change", "blur"] },
};

async function onFormFondsChange(id: string | null) {
  formData.catalog_id = null;
  formCatalogs.value = id ? (await CatalogAPI.list(id)).data : [];
  const fonds = fondsList.value.find((f) => f.id === id);
  if (fonds) formModel.value.QZH = fonds.fonds_code;
}

// 选门类 → 新增时自动填档号（有历史末位+1；无历史按门类档号规则生成第一条；用户可改）
async function onFormCategoryChange(id: string | null) {
  if (!id || isEdit.value) return;
  try {
    const res = await OrganizeAPI.nextDh(id, {
      qzh: (formModel.value.QZH as string) || undefined,
      nd: (formModel.value.ND as number) || undefined,
      fonds_id: formData.fonds_id || undefined,
      catalog_id: formData.catalog_id || undefined,
    });
    if (res.data?.dh) formModel.value.DH = res.data.dh;
  } catch { /* 取不到不阻断 */ }
}

function openModal(row: Archive | null) {
  if (row) {
    isEdit.value = true;
    editId.value = row.id;
    Object.assign(formData, {
      fonds_id: row.fonds_id, catalog_id: row.catalog_id, category_id: row.category_id,
    });
    formModel.value = {
      TM: row.TM, QZH: row.QZH, RZZ: row.RZZ ?? "", ND: row.ND ?? null,
      WJRQ: row.WJRQ ?? "", YS: row.YS ?? null, MJ: row.MJ, BGQX: row.BGQX, DH: row.DH ?? "",
      ...(row.ext_fields ?? {}),
    };
  } else {
    isEdit.value = false;
    editId.value = null;
    Object.assign(formData, emptyForm());
    formModel.value = { ND: new Date().getFullYear() };  // 年度默认当年
    if (filter.fonds_id) {
      formData.fonds_id = filter.fonds_id;
      onFormFondsChange(filter.fonds_id);
    }
    if (filter.catalog_id) formData.catalog_id = filter.catalog_id;
    if (filter.category_id) {
      formData.category_id = filter.category_id;
      onFormCategoryChange(filter.category_id);  // 预选门类时自动填档号
    }
  }
  modalVisible.value = true;
}

/** 把扁平著录模型拆成 base 列 + ext_fields */
function splitModel() {
  const m = formModel.value;
  const names = dynFormRef.value?.fieldNames() ?? Object.keys(m);
  const ext: Record<string, unknown> = {};
  for (const n of names) {
    if (!BASE_COLUMNS.includes(n) && m[n] != null && m[n] !== "") ext[n] = m[n];
  }
  const s = (k: string) => (m[k] == null || m[k] === "" ? undefined : String(m[k]));
  const n = (k: string) => (m[k] == null || m[k] === "" ? undefined : Number(m[k]));
  return { m, ext, s, n };
}

async function submitForm() {
  await formRef.value?.validate();
  const missing = dynFormRef.value?.validate() ?? [];
  if (missing.length) {
    message.error(`请填写必录字段：${missing.join("、")}`);
    return;
  }
  const { ext, s, n } = splitModel();
  saving.value = true;
  try {
    if (isEdit.value && editId.value) {
      const payload: ArchiveUpdate = {
        TM: s("TM"), RZZ: s("RZZ"), ND: n("ND"), WJRQ: s("WJRQ"), YS: n("YS"),
        MJ: s("MJ") as ArchiveUpdate["MJ"], BGQX: s("BGQX") as ArchiveUpdate["BGQX"],
        DH: s("DH"), ext_fields: Object.keys(ext).length ? ext : undefined,
      };
      await ArchiveAPI.update(editId.value, payload);
      message.success("已更新");
    } else {
      const payload: ArchiveCreate = {
        fonds_id: formData.fonds_id!, catalog_id: formData.catalog_id!, category_id: formData.category_id!,
        TM: s("TM") ?? "", QZH: s("QZH") ?? "", RZZ: s("RZZ"), ND: n("ND"),
        WJRQ: s("WJRQ"), YS: n("YS"),
        MJ: (s("MJ") ?? "无") as ArchiveCreate["MJ"], BGQX: (s("BGQX") ?? "long") as ArchiveCreate["BGQX"],
        DH: s("DH"), ext_fields: Object.keys(ext).length ? ext : undefined,
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
    content: `确认删除档案「${row.TM}」？`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      await ArchiveAPI.remove(row.id);
      message.success("已删除");
      detailVisible.value = false;
      await loadArchives();
    },
  });
}

function confirmBatchDelete() {
  if (selectedIds.value.length === 0) return;
  dialog.warning({
    title: "批量删除确认",
    content: `确认删除选中的 ${selectedIds.value.length} 条档案？删除后不可恢复。`,
    positiveText: "删除",
    negativeText: "取消",
    onPositiveClick: async () => {
      const res = await OrganizeAPI.batchDelete(selectedIds.value);
      message.success(`已删除 ${res.data.deleted} 条`);
      selectedIds.value = [];
      await loadArchives();
    },
  });
}

// ── 整理工具 ─────────────────────────────────────────────────────────────────
const showAttachWizard = ref(false);
const showRenumber = ref(false);
const showBatchEdit = ref(false);

function onOrganizeDone() {
  selectedIds.value = [];
  loadArchives();
}

function confirmArchiveToFormal() {
  dialog.warning({
    title: "归档入库",
    content: `确认将选中的 ${selectedIds.value.length} 条档案从暂存库转入正式库？转入后档案进入正式管理流程（鉴定 / 利用 / 统计）。`,
    positiveText: "确认归档",
    negativeText: "取消",
    onPositiveClick: async () => {
      const res = await OrganizeAPI.archiveToFormal(selectedIds.value);
      if (res.code !== 0) {
        message.error(res.message);
        return;
      }
      const { archived, failed, rows } = res.data;
      if (failed === 0) {
        message.success(`已归档入库 ${archived} 条`);
      } else {
        const reasons = rows
          .filter((r) => r.status === "failed")
          .slice(0, 5)
          .map((r) => `「${r.TM}」：${r.reason}`)
          .join("\n");
        dialog.error({
          title: `归档完成：成功 ${archived} 条，失败 ${failed} 条`,
          content: reasons,
          positiveText: "知道了",
        });
      }
      onOrganizeDone();
    },
  });
}

// ── 初始化 ───────────────────────────────────────────────────────────────────
onMounted(async () => {
  const kw = route.query.keyword;
  if (typeof kw === "string" && kw) filter.keyword = kw;
  loadArchives();
  const [fondsRes, categoryRes] = await Promise.all([FondsAPI.list(), CategoryAPI.list()]);
  fondsList.value = fondsRes.data ?? [];
  categoryList.value = categoryRes.data ?? [];
});
</script>
