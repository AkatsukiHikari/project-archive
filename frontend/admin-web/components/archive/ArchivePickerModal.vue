<template>
  <NModal
    :show="show"
    preset="card"
    :title="title"
    :z-index="zIndex"
    style="width: 1040px; max-width: 96vw"
    @update:show="(v: boolean) => emit('update:show', v)"
  >
    <div class="flex flex-col gap-3">
      <!-- 检索条件 -->
      <div class="flex flex-wrap items-center gap-2">
        <NInput v-model:value="form.keyword" placeholder="题名 / 责任者 / 档号 关键词" clearable style="width: 260px" @keyup.enter="search">
          <template #prefix><Icon name="heroicons:magnifying-glass" class="w-4 h-4 text-gray-400" /></template>
        </NInput>
        <NSelect v-model:value="form.fonds_id" :options="fondsOptions" placeholder="全部全宗" clearable filterable style="width: 150px" />
        <NInput v-model:value="form.DH" placeholder="档号" clearable style="width: 130px" />
        <NInputNumber v-model:value="form.ND" placeholder="年度" clearable :show-button="false" style="width: 96px" />
        <NButton type="primary" :loading="loading" @click="search">检索</NButton>
        <NButton tertiary @click="resetForm">重置</NButton>
      </div>

      <NDataTable
        v-model:checked-row-keys="selected"
        :columns="columns"
        :data="rows"
        :loading="loading"
        :row-key="(r: Archive) => r.id"
        :pagination="false"
        max-height="420"
        size="small"
      />

      <div class="flex items-center justify-between">
        <span class="text-sm text-gray-500">
          共 <strong>{{ total }}</strong> 条 · 已勾选 <strong>{{ selected.length }}</strong> 件
        </span>
        <NPagination
          v-model:page="page"
          :page-count="pageCount"
          :page-size="pageSize"
          :page-sizes="[10, 20, 50]"
          show-size-picker
          @update:page="load"
          @update:page-size="onPageSize"
        />
      </div>
    </div>

    <template #footer>
      <div class="flex items-center justify-end gap-3">
        <NButton @click="emit('update:show', false)">取消</NButton>
        <NButton type="primary" :disabled="!selected.length" @click="confirm">
          <template #icon><Icon name="heroicons:plus" class="w-4 h-4" /></template>
          加入档案库（{{ selected.length }}）
        </NButton>
      </div>
    </template>
  </NModal>
</template>

<script setup lang="tsx">
import { computed, h, onMounted, reactive, ref } from "vue";
import { NButton, NDataTable, NInput, NInputNumber, NModal, NPagination, NSelect, NTag } from "naive-ui";
import type { DataTableColumns } from "naive-ui";
import { ArchiveAPI, FondsAPI, type Archive, type Fonds } from "@/api/repository";

const props = withDefaults(
  defineProps<{ show: boolean; title?: string; excludeIds?: string[]; zIndex?: number }>(),
  { title: "从馆藏选档加入成果档案库", excludeIds: () => [], zIndex: 2000 },
);
const emit = defineEmits<{
  (e: "update:show", v: boolean): void;
  (e: "confirm", ids: string[]): void;
  (e: "view", a: { archive_id: string; TM: string; DH: string }): void;
}>();

const form = reactive<{ keyword: string; fonds_id: string | null; DH: string; ND: number | null }>({
  keyword: "", fonds_id: null, DH: "", ND: null,
});
const loading = ref(false);
const rows = ref<Archive[]>([]);
const selected = ref<string[]>([]);
const page = ref(1);
const pageSize = ref(10);
const total = ref(0);
const pageCount = computed(() => Math.max(1, Math.ceil(total.value / pageSize.value)));

const excludeSet = computed(() => new Set(props.excludeIds));

const columns: DataTableColumns<Archive> = [
  { type: "selection", disabled: (r: Archive) => excludeSet.value.has(r.id) },
  { title: "档号", key: "DH", width: 160, render: (r) => r.DH || "—" },
  { title: "题名", key: "TM", ellipsis: { tooltip: true }, minWidth: 220 },
  { title: "责任者", key: "RZZ", width: 110, render: (r) => r.RZZ || "—" },
  { title: "年度", key: "ND", width: 70, render: (r) => r.ND || "—" },
  { title: "全宗", key: "QZH", width: 90 },
  {
    title: "原文", key: "src", width: 96,
    render: (r) =>
      r.attachment_count
        ? h(NButton, { size: "tiny", tertiary: true, type: "primary", onClick: () => emit("view", { archive_id: r.id, TM: r.TM, DH: r.DH || "" }) },
            { default: () => "查看原文" })
        : h("span", { class: "text-xs text-gray-300" }, "无原文"),
  },
  {
    title: "", key: "added", width: 64,
    render: (r) => excludeSet.value.has(r.id)
      ? h(NTag, { size: "small", type: "success", round: true }, { default: () => "已加入" })
      : null,
  },
];

async function load() {
  loading.value = true;
  try {
    const res = await ArchiveAPI.list({
      keyword: form.keyword || undefined,
      fonds_id: form.fonds_id || undefined,
      DH: form.DH || undefined,
      ND: form.ND ?? undefined,
      page: page.value,
      page_size: pageSize.value,
    });
    rows.value = res.data.items;
    total.value = res.data.total;
  } finally {
    loading.value = false;
  }
}

function search() {
  page.value = 1;
  load();
}

function onPageSize(s: number) {
  pageSize.value = s;
  page.value = 1;
  load();
}

function confirm() {
  const ids = selected.value.filter((id) => !excludeSet.value.has(id));
  if (!ids.length) return;
  emit("confirm", ids);
  selected.value = [];
}

function resetForm() {
  form.keyword = "";
  form.fonds_id = null;
  form.DH = "";
  form.ND = null;
  page.value = 1;
  selected.value = [];
  load();
}

// 供父组件在打开时重置
function reset() {
  resetForm();
}

const fondsOptions = ref<{ label: string; value: string }[]>([]);
async function loadFonds() {
  try {
    const res = await FondsAPI.list();
    fondsOptions.value = (res.data ?? []).map((f: Fonds) => ({ label: `${f.fonds_code} ${f.name}`, value: f.id }));
  } catch {
    fondsOptions.value = [];
  }
}

onMounted(loadFonds);
defineExpose({ reset });
</script>
