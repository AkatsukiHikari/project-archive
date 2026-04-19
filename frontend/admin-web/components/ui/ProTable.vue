<template>
  <div class="pro-card">
    <!-- 工具栏 -->
    <div
      v-if="$slots['toolbar-left'] || $slots['toolbar-right']"
      class="pro-toolbar"
    >
      <div class="flex items-center gap-2.5 flex-wrap flex-1 min-w-0">
        <slot name="toolbar-left" />
      </div>
      <div class="flex items-center gap-2 shrink-0">
        <slot name="toolbar-right" />
      </div>
    </div>

    <!-- 表格 -->
    <NDataTable
      v-bind="$attrs"
      :columns="(columns as any)"
      :data="(data as any)"
      :loading="loading"
      :row-key="(row: Record<string, unknown>) => row[rowKey] as string"
      :pagination="paginationConfig"
      :remote="remote"
    >
      <template #empty>
        <NEmpty :description="emptyContent" class="py-10" />
      </template>
    </NDataTable>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { NDataTable, NEmpty } from "naive-ui";

/**
 * ProTable —— 统一 CRUD 表格容器
 *
 * 分页模式：
 *   1. 客户端分页（默认）：传 :data 全量，pageSize 默认 20
 *   2. 服务端分页：传 :total :current-page，监听 @page-change
 *   3. 禁用分页：:page-size="0"
 */
defineOptions({ inheritAttrs: false });

const props = withDefaults(
  defineProps<{
    columns: unknown[];
    data: unknown[];
    loading?: boolean;
    rowKey?: string;
    emptyContent?: string;
    /** 每页条数，默认 20；传 0 禁用分页 */
    pageSize?: number;
    /** 服务端分页：总记录数 */
    total?: number;
    /** 服务端分页：当前页（1-based） */
    currentPage?: number;
    /** 是否服务端分页（配合 total + currentPage 使用） */
    remote?: boolean;
  }>(),
  {
    loading: false,
    rowKey: "id",
    emptyContent: "暂无数据",
    pageSize: 20,
    total: undefined,
    currentPage: undefined,
    remote: false,
  },
);

const emit = defineEmits<{
  (e: "page-change", page: number, pageSize: number): void;
}>();

const paginationConfig = computed(() => {
  if (props.pageSize === 0) return false;

  const base = {
    pageSize: props.pageSize,
    showSizePicker: true,
    pageSizes: [10, 20, 50, 100],
    prefix: ({ itemCount }: { itemCount: number | undefined }) => `共 ${itemCount ?? 0} 条`,
  };

  if (props.total !== undefined) {
    // 服务端分页
    return {
      ...base,
      itemCount: props.total,
      page: props.currentPage ?? 1,
      onChange: (page: number) => emit("page-change", page, props.pageSize),
      onUpdatePageSize: (size: number) => emit("page-change", 1, size),
    };
  }

  // 客户端分页
  return base;
});
</script>

<style scoped>
.pro-card {
  background: var(--semi-color-bg-0);
  border: 1px solid var(--semi-color-border);
  border-radius: 12px;
  overflow: hidden;
  /* 分页区域下方留出呼吸空间 */
  padding-bottom: 4px;
}

.pro-toolbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 16px;
  border-bottom: 1px solid var(--semi-color-border);
  gap: 12px;
  background: var(--semi-color-bg-0);
}
</style>
