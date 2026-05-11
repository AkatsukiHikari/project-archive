<template>
  <div class="rounded-xl overflow-hidden border border-base-content/10 bg-base-100">

    <!-- 搜索表单（可折叠） -->
    <Transition name="search-panel">
      <ProTableSearch
        v-if="searchableColumns.length > 0 && searchPanelOpen"
        :columns="searchableColumns"
        :threshold="searchCollapseThreshold"
        @search="applySearch"
        @reset="clearSearch"
      />
    </Transition>

    <!-- 工具栏 -->
    <div
      v-if="searchableColumns.length > 0 || $slots['toolbar-left'] || $slots['toolbar-right']"
      class="flex items-center justify-between px-4 py-2.5 border-b border-base-content/10 gap-3"
    >
      <div class="flex items-center gap-2.5 flex-wrap flex-1 min-w-0">
        <slot name="toolbar-left" />
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <slot name="toolbar-right" />
        <NButton
          v-if="searchableColumns.length > 0"
          size="small"
          quaternary
          class="opacity-50 hover:opacity-100"
          @click="searchPanelOpen = !searchPanelOpen"
        >
          <template #icon>
            <Icon
              :name="searchPanelOpen ? 'heroicons:chevron-up' : 'heroicons:funnel'"
              class="w-3.5 h-3.5"
            />
          </template>
          {{ searchPanelOpen ? '收起查询' : '展开查询' }}
        </NButton>
      </div>
    </div>

    <!-- 表格 -->
    <NDataTable
      v-bind="$attrs"
      :columns="(processedColumns as any)"
      :data="(filteredData as any)"
      :loading="loading"
      :row-key="(row: Record<string, unknown>) => row[rowKey] as string"
      :pagination="paginationConfig"
      :remote="remote"
    >
      <template #empty>
        <NEmpty :description="emptyContent" class="py-10" />
      </template>
    </NDataTable>

    <!-- 无分页时底部计数 -->
    <div
      v-if="pageSize === 0"
      class="flex items-center justify-end px-4 py-1.5 text-xs text-base-content/50 border-t border-base-content/10"
    >
      共 {{ displayTotal }} 条
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed, reactive, ref } from "vue";
import { NDataTable, NEmpty, NButton } from "naive-ui";
import ProTableSearch, { type SearchableColumn } from "./Search.vue";

interface InternalColumn {
  key?: string | number;
  title?: string;
  type?: string;
  resizable?: boolean;
  search?: SearchableColumn["search"];
}

defineOptions({ inheritAttrs: false });

const props = withDefaults(
  defineProps<{
    columns: unknown[];
    data: unknown[];
    loading?: boolean;
    rowKey?: string;
    emptyContent?: string;
    pageSize?: number;
    total?: number;
    currentPage?: number;
    remote?: boolean;
    searchCollapseThreshold?: number;
  }>(),
  {
    loading: false,
    rowKey: "id",
    emptyContent: "暂无数据",
    pageSize: 20,
    total: undefined,
    currentPage: undefined,
    remote: false,
    searchCollapseThreshold: 3,
  },
);

const emit = defineEmits<{
  (e: "page-change", page: number, pageSize: number): void;
}>();

// ── 搜索面板折叠 ──────────────────────────────────────────────────────────────

const searchPanelOpen = ref(true);

// ── 搜索 ──────────────────────────────────────────────────────────────────────

const activeSearch = reactive<Record<string, string>>({});

const searchableColumns = computed<SearchableColumn[]>(() =>
  (props.columns as InternalColumn[])
    .filter((col) => col.search && col.key != null)
    .map((col) => ({ key: col.key!, title: col.title, search: col.search! })),
);

function applySearch(values: Record<string, string>) {
  for (const [k, v] of Object.entries(values)) {
    activeSearch[k] = v;
  }
}

function clearSearch() {
  for (const key of Object.keys(activeSearch)) {
    activeSearch[key] = "";
  }
}

const filteredData = computed(() => {
  const hasQuery = Object.values(activeSearch).some((v) => v?.length > 0);
  if (!hasQuery) return props.data;

  return props.data.filter((row) => {
    const r = row as Record<string, unknown>;
    for (const col of searchableColumns.value) {
      const key = String(col.key);
      const query = activeSearch[key];
      if (!query) continue;
      const cell = r[key];
      if (col.search.type === "select") {
        if (String(cell) !== query) return false;
      } else {
        if (!String(cell ?? "").toLowerCase().includes(query.toLowerCase())) return false;
      }
    }
    return true;
  });
});

// ── 列宽拖拽 ──────────────────────────────────────────────────────────────────

const SKIP_RESIZE = new Set(["selection", "expand"]);

const processedColumns = computed(() =>
  (props.columns as InternalColumn[]).map((col) => {
    if (SKIP_RESIZE.has(col.type ?? "") || col.key === "actions") return col;
    if (col.resizable === false) return col;
    return { ...col, resizable: true };
  }),
);

// ── 分页 ──────────────────────────────────────────────────────────────────────

const displayTotal = computed(() =>
  props.total !== undefined ? props.total : filteredData.value.length,
);

const paginationConfig = computed(() => {
  if (props.pageSize === 0) return false;

  const base = {
    pageSize: props.pageSize,
    showSizePicker: true,
    pageSizes: [10, 20, 50, 100],
    prefix: ({ itemCount }: { itemCount: number | undefined }) =>
      `共 ${itemCount ?? 0} 条`,
  };

  if (props.total !== undefined) {
    return {
      ...base,
      itemCount: props.total,
      page: props.currentPage ?? 1,
      onChange: (page: number) => emit("page-change", page, props.pageSize),
      onUpdatePageSize: (size: number) => emit("page-change", 1, size),
    };
  }

  return { ...base, itemCount: filteredData.value.length };
});
</script>

<style scoped>
:deep(.n-data-table__pagination) {
  padding: 6px 16px !important;
}

.search-panel-enter-active,
.search-panel-leave-active {
  transition: max-height 0.22s ease, opacity 0.18s ease;
  overflow: hidden;
}

.search-panel-enter-from,
.search-panel-leave-to {
  max-height: 0;
  opacity: 0;
}

.search-panel-enter-to,
.search-panel-leave-from {
  max-height: 400px;
  opacity: 1;
}
</style>
