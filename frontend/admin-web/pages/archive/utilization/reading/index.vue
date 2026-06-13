<template>
  <div class="flex flex-col gap-3 min-h-0 flex-1">
    <div class="flex items-start justify-between gap-3">
      <AdminPageHeader
        title="档案查阅"
        description="输入关键词查找档案，可按年代、全宗、门类等细分筛选"
        icon="heroicons:magnifying-glass-circle"
      />
      <!-- 当前办理人（点头像看详情，可办结） -->
      <div
        v-if="currentApp"
        class="flex items-center gap-2 pro-card px-3 py-2 cursor-pointer shrink-0"
        @click="showPerson = true"
      >
        <PersonAvatar :name="currentApp.applicant_name" :size="36" />
        <div class="flex flex-col">
          <span class="text-[13px] font-medium leading-tight" style="color:var(--semi-color-text-0)">{{ currentApp.applicant_name }}</span>
          <span class="text-[11px]" style="color:var(--semi-color-text-3)">办理中 · 调阅篮 {{ currentApp.item_count }} 件</span>
        </div>
        <Icon name="heroicons:chevron-down" class="w-4 h-4" style="color:var(--semi-color-text-3)" />
      </div>
    </div>

    <!-- ── 组合检索区 ─────────────────────────────────────── -->
    <div class="pro-card p-4 flex flex-col gap-3">
      <div class="flex flex-wrap items-center gap-3">
        <NInput v-model:value="form.keyword" placeholder="题名 / 责任者 / 档号" clearable style="width: 320px" @keydown.enter="search">
          <template #prefix><Icon name="heroicons:magnifying-glass" class="w-4 h-4 text-gray-400" /></template>
        </NInput>
        <NButton type="primary" :loading="loading" @click="search">查询</NButton>
        <NButton tertiary @click="reset">重置</NButton>
        <NButton text type="primary" @click="advanced = !advanced">
          <Icon :name="advanced ? 'heroicons:chevron-up' : 'heroicons:adjustments-horizontal'" class="w-4 h-4 mr-1" />
          {{ advanced ? "收起" : "细分筛选" }}
        </NButton>
        <NTag v-if="publicOnly" size="small" type="warning" round>仅检索公开档案</NTag>
        <div class="flex-1" />
        <span class="text-sm text-gray-500">共 <strong>{{ total }}</strong> 条</span>
      </div>

      <div v-show="advanced" class="grid grid-cols-2 lg:grid-cols-4 gap-x-4 gap-y-3 pt-1 border-t" style="border-color: var(--semi-color-border)">
        <Field label="题名"><NInput v-model:value="form.TM" placeholder="题名关键字" clearable /></Field>
        <Field label="责任者"><NInput v-model:value="form.RZZ" placeholder="责任者" clearable /></Field>
        <Field label="档号"><NInput v-model:value="form.DH" placeholder="档号" clearable /></Field>
        <Field label="全宗"><NSelect v-model:value="form.fonds_id" :options="fondsOptions" placeholder="全部全宗" clearable filterable /></Field>
        <Field label="门类"><NSelect v-model:value="form.category_id" :options="categoryOptions" placeholder="全部门类" clearable filterable /></Field>
        <Field label="密级"><NSelect v-model:value="form.MJ" :options="mjOptions" placeholder="全部" clearable :disabled="publicOnly" /></Field>
        <Field label="保管期限"><NSelect v-model:value="form.BGQX" :options="bgqxOptions" placeholder="全部" clearable /></Field>
        <Field label="年度">
          <div class="flex items-center gap-1">
            <NInputNumber v-model:value="form.ND_from" :show-button="false" placeholder="起" class="flex-1" />
            <span class="text-gray-400">~</span>
            <NInputNumber v-model:value="form.ND_to" :show-button="false" placeholder="止" class="flex-1" />
          </div>
        </Field>
      </div>
    </div>

    <!-- ── 结果表 ─────────────────────────────────────────── -->
    <div class="pro-card p-4 flex-1 min-h-0 flex flex-col gap-3">
      <div v-if="currentApp" class="flex items-center gap-3">
        <span class="text-sm" style="color:var(--semi-color-text-2)">已选 <strong>{{ selected.size }}</strong> 件</span>
        <NButton size="small" type="primary" :disabled="selected.size === 0" @click="addToBasket">
          <template #icon><Icon name="heroicons:shopping-bag" class="w-4 h-4" /></template>
          加入调阅篮
        </NButton>
        <div class="flex-1" />
        <NButton size="small" type="success" @click="completeApp">
          <template #icon><Icon name="heroicons:check-circle" class="w-4 h-4" /></template>
          办理完成
        </NButton>
      </div>
      <ProTable :columns="columns" :data="rows" :loading="loading" :page-size="0" size="small" />
      <div class="flex justify-end">
        <NPagination v-model:page="page" :page-count="pageCount" :page-size="pageSize" show-quick-jumper @update:page="load" />
      </div>
    </div>

    <!-- 档案详情抽屉 -->
    <NDrawer v-model:show="showDetail" :width="560" placement="right">
      <NDrawerContent :title="`档案详情 · ${detail?.DH || ''}`" closable>
        <div v-if="detail" class="flex flex-col gap-4">
          <table class="w-full text-[13px] border-collapse">
            <tbody>
              <tr v-for="f in detailFields" :key="f.label" class="border-b" style="border-color: var(--semi-color-border)">
                <th class="text-left align-top py-2 pr-3 font-medium whitespace-nowrap" style="width:96px;color:var(--semi-color-text-3)">{{ f.label }}</th>
                <td class="py-2 break-words" :class="f.mono ? 'font-mono' : ''" style="color:var(--semi-color-text-0)">{{ f.value || "—" }}</td>
              </tr>
            </tbody>
          </table>
        </div>
        <template #footer>
          <div class="flex justify-end gap-2">
            <NButton @click="showDetail = false">关闭</NButton>
            <NButton type="primary" @click="openReader()">
              <template #icon><Icon name="heroicons:document-text" class="w-4 h-4" /></template>
              查看原文
            </NButton>
          </div>
        </template>
      </NDrawerContent>
    </NDrawer>

    <!-- 办理人详情抽屉（复用组件，与利用申请页一致） -->
    <NDrawer v-model:show="showPerson" :width="480" placement="right">
      <NDrawerContent :title="`利用登记 · ${currentApp?.reg_no || ''}`" closable>
        <ApplicationDetailPanel :app-id="appId" :show-actions="false" @changed="reloadApp" />
      </NDrawerContent>
    </NDrawer>
  </div>
</template>

<script setup lang="tsx">
import { ref, reactive, computed, onMounted, h } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NInput, NInputNumber, NSelect, NButton, NPagination, NTag, NCheckbox, NDrawer, NDrawerContent, useMessage, useDialog } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";
import { PersonAvatar, ApplicationDetailPanel } from "@/components/archive";
import { FondsAPI, CategoryAPI, ArchiveAPI } from "@/api/repository";
import type { Fonds, ArchiveCategory, Archive, ArchiveListParams } from "@/api/repository";
import { UtilizationAPI } from "@/api/utilization";
import type { UtilApplication, ItemIn } from "@/api/utilization";

definePageMeta({ layout: "archive", middleware: "auth" });

const route = useRoute();
const router = useRouter();
const message = useMessage();
const dialog = useDialog();

const appId = computed(() => (route.query.app ? String(route.query.app) : null));
const publicOnly = computed(() => !!appId.value);  // 社会大众查档：仅公开

const mjOptions = [
  { label: "无", value: "无" }, { label: "秘密", value: "秘密" },
  { label: "机密", value: "机密" }, { label: "绝密", value: "绝密" }, { label: "绝密", value: "top_secret" },
];
const bgqxOptions = [{ label: "永久", value: "permanent" }, { label: "长期", value: "long" }, { label: "短期", value: "short" }];
const MJ_LABEL: Record<string, string> = { public: "公开", internal: "内部", secret: "秘密", confidential: "机密", top_secret: "绝密" };
const BGQX_LABEL: Record<string, string> = { permanent: "永久", long: "长期", short: "短期" };
const MJ_TONE: Record<string, "default" | "warning" | "error"> = { public: "default", internal: "default", secret: "warning", confidential: "error", top_secret: "error" };

const Field = (props: { label: string }, { slots }: { slots: { default?: () => unknown } }) =>
  h("div", { class: "flex flex-col gap-1" }, [h("span", { class: "text-xs text-gray-500" }, props.label), slots.default?.()]);

const advanced = ref(false);
const form = reactive<ArchiveListParams>({
  keyword: "", TM: "", RZZ: "", DH: "",
  fonds_id: undefined, category_id: undefined, MJ: undefined, BGQX: undefined,
  ND_from: undefined, ND_to: undefined,
});

// ── 选项 / 映射 ───────────────────────────────────────────────────
const fondsList = ref<Fonds[]>([]);
const categoryMap = ref<Record<string, string>>({});
const fondsOptions = computed(() => fondsList.value.map((f) => ({ label: `${f.fonds_code} - ${f.name}`, value: f.id })));
const categoryOptions = ref<{ label: string; value: string }[]>([]);
const catName = (id: string) => categoryMap.value[id] ?? id.slice(0, 8);

// ── 当前办理人 ────────────────────────────────────────────────────
const currentApp = ref<UtilApplication | null>(null);
const showPerson = ref(false);
async function reloadApp() {
  if (!appId.value) { currentApp.value = null; return; }
  currentApp.value = (await UtilizationAPI.get(appId.value)).data;
}

// ── 列表（服务端分页） ────────────────────────────────────────────
const loading = ref(false);
const rows = ref<Archive[]>([]);
const total = ref(0);
const page = ref(1);
const pageSize = ref(20);
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)));
const selected = ref<Set<string>>(new Set());

function buildParams(): ArchiveListParams {
  const clean = (v?: string) => (v && v.trim() ? v.trim() : undefined);
  return {
    keyword: clean(form.keyword), TM: clean(form.TM), RZZ: clean(form.RZZ), DH: clean(form.DH),
    fonds_id: form.fonds_id || undefined, category_id: form.category_id || undefined,
    MJ: publicOnly.value ? "public" : (form.MJ || undefined),
    BGQX: form.BGQX || undefined,
    ND_from: form.ND_from ?? undefined, ND_to: form.ND_to ?? undefined,
    page: page.value, page_size: pageSize.value,
  };
}

async function load() {
  loading.value = true;
  try {
    const res = await ArchiveAPI.list(buildParams());
    rows.value = res.data.items;
    total.value = res.data.total;
  } finally {
    loading.value = false;
  }
}
function search() { page.value = 1; load(); }
function reset() {
  Object.assign(form, { keyword: "", TM: "", RZZ: "", DH: "", fonds_id: undefined, category_id: undefined, MJ: undefined, BGQX: undefined, ND_from: undefined, ND_to: undefined });
  page.value = 1; load();
}

function toggle(id: string, checked: boolean) {
  const s = new Set(selected.value);
  if (checked) s.add(id); else s.delete(id);
  selected.value = s;
}
function toggleAll(checked: boolean) {
  selected.value = checked ? new Set(rows.value.map((r) => r.id)) : new Set();
}
const allChecked = computed(() => rows.value.length > 0 && rows.value.every((r) => selected.value.has(r.id)));

const columns = computed<DataTableColumns<Archive>>(() => {
  const base: DataTableColumns<Archive> = [
    { title: "档号", key: "DH", width: 170, render: (r) => h("span", { class: "font-mono text-[12px]" }, r.DH || "—") },
    { title: "题名", key: "TM", minWidth: 220, ellipsis: { tooltip: true } },
    { title: "责任者", key: "RZZ", width: 110, render: (r) => r.RZZ || "—" },
    { title: "年度", key: "ND", width: 70, render: (r) => r.ND ?? "—" },
    { title: "全宗号", key: "QZH", width: 90 },
    { title: "门类", key: "category_id", width: 130, render: (r) => catName(r.category_id) },
    { title: "密级", key: "MJ", width: 70, render: (r) => h(NTag, { size: "small", type: MJ_TONE[r.MJ] ?? "default" }, () => MJ_LABEL[r.MJ] ?? r.MJ) },
    { title: "保管期限", key: "BGQX", width: 80, render: (r) => BGQX_LABEL[r.BGQX] ?? r.BGQX },
    {
      title: "操作", key: "actions", width: 130, fixed: "right",
      render: (r) => h("div", { class: "flex gap-2" }, [
        h(NButton, { size: "small", tertiary: true, onClick: () => openDetail(r) }, () => "详情"),
        h(NButton, { size: "small", tertiary: true, type: "primary", onClick: () => openReaderFor(r) }, () => "原文"),
      ]),
    },
  ];
  if (!appId.value) return base;
  // 办理上下文：行首加勾选框
  return [
    {
      key: "_sel", width: 44,
      title: () => h(NCheckbox, { checked: allChecked.value, onUpdateChecked: (c: boolean) => toggleAll(c) }),
      render: (r) => h(NCheckbox, { checked: selected.value.has(r.id), onUpdateChecked: (c: boolean) => toggle(r.id, c) }),
    },
    ...base,
  ];
});

// ── 调阅篮 / 办结 ─────────────────────────────────────────────────
async function addToBasket() {
  if (!appId.value || selected.value.size === 0) return;
  const items: ItemIn[] = rows.value
    .filter((r) => selected.value.has(r.id))
    .map((r) => ({ archive_id: r.id, DH: r.DH ?? null, TM: r.TM, RZZ: r.RZZ ?? null, ND: r.ND ?? null, QZH: r.QZH }));
  const res = await UtilizationAPI.addItems(appId.value, items);
  message.success(`已加入 ${res.data.added} 件（去重后）`);
  selected.value = new Set();
  await reloadApp();
}
function completeApp() {
  if (!appId.value) return;
  dialog.success({
    title: "办理完成",
    content: `确认为「${currentApp.value?.applicant_name}」办结本次利用？调阅篮共 ${currentApp.value?.item_count ?? 0} 件。`,
    positiveText: "确认办结", negativeText: "取消",
    onPositiveClick: async () => {
      await UtilizationAPI.complete(appId.value!);
      message.success("已办理完成");
      router.push("/archive/utilization/apply");
    },
  });
}

// ── 档案详情抽屉 ──────────────────────────────────────────────────
const showDetail = ref(false);
const detail = ref<Archive | null>(null);
const detailFields = computed(() => {
  const a = detail.value;
  if (!a) return [];
  return [
    { label: "档号", value: a.DH, mono: true },
    { label: "题名", value: a.TM, mono: false },
    { label: "责任者", value: a.RZZ, mono: false },
    { label: "年度", value: a.ND ? `${a.ND} 年` : "", mono: false },
    { label: "文件日期", value: a.WJRQ, mono: false },
    { label: "页数", value: a.YS ? `${a.YS} 页` : "", mono: false },
    { label: "全宗号", value: a.QZH, mono: true },
    { label: "门类", value: catName(a.category_id), mono: false },
    { label: "密级", value: MJ_LABEL[a.MJ] ?? a.MJ, mono: false },
    { label: "保管期限", value: BGQX_LABEL[a.BGQX] ?? a.BGQX, mono: false },
  ];
});
function openDetail(r: Archive) { detail.value = r; showDetail.value = true; }
function openReader(id?: string) {
  const aid = id ?? detail.value?.id;
  if (aid) router.push(`/archive/reader?id=${aid}`);
}
function openReaderFor(r: Archive) { router.push(`/archive/reader?id=${r.id}`); }

onMounted(async () => {
  const [f, c] = await Promise.all([FondsAPI.list(), CategoryAPI.list()]);
  fondsList.value = f.data;
  categoryMap.value = Object.fromEntries(c.data.map((x: ArchiveCategory) => [x.id, `${x.code} - ${x.name}`]));
  categoryOptions.value = c.data.map((x: ArchiveCategory) => ({ label: `${x.code} - ${x.name}`, value: x.id }));
  await reloadApp();
  await load();
});
</script>
