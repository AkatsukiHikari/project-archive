<template>
  <div class="flex flex-col h-full gap-0">
    <!-- 顶部栏 -->
    <div class="designer-header">
      <div class="flex items-center gap-3">
        <NButton text @click="router.back()">
          <template #icon><Icon name="heroicons:arrow-left" class="w-4 h-4" /></template>
        </NButton>
        <div>
          <div class="text-base font-semibold">录入排版设计</div>
          <div class="text-xs text-gray-400">{{ category?.name }} · 拖拽字段到画布，定义表单布局</div>
        </div>
      </div>
      <div class="flex items-center gap-2">
        <NButton @click="clearLayout">清空画布</NButton>
        <NButton type="primary" :loading="saving" @click="saveLayout">
          <template #icon><Icon name="heroicons:check" class="w-4 h-4" /></template>
          保存排版
        </NButton>
      </div>
    </div>

    <div v-if="loading" class="flex-1 flex items-center justify-center">
      <NSpin size="large" />
    </div>

    <div v-else class="designer-body">
      <!-- 左侧：字段库 -->
      <div class="field-pool">
        <div class="pool-title">
          <Icon name="heroicons:list-bullet" class="w-4 h-4" />
          字段库
          <span class="pool-count">{{ poolFields.length }} 个可用</span>
        </div>

        <div class="pool-search">
          <NInput
            v-model:value="poolSearch"
            size="small"
            placeholder="搜索字段..."
            clearable
          >
            <template #prefix><Icon name="heroicons:magnifying-glass" class="w-3.5 h-3.5" /></template>
          </NInput>
        </div>

        <div class="pool-list">
          <div
            v-for="field in filteredPoolFields"
            :key="field.name"
            class="pool-field"
            :class="{ 'pool-field--inherited': field.inherited }"
            draggable="true"
            @dragstart="onPoolDragStart(field)"
          >
            <div class="pool-field-label">{{ field.label }}</div>
            <div class="pool-field-meta">
              <code>{{ field.name }}</code>
              <NTag v-if="field.inherited" size="tiny" type="info">继承</NTag>
              <NTag size="tiny">{{ fieldTypeLabel(field.type) }}</NTag>
            </div>
          </div>
          <div v-if="filteredPoolFields.length === 0" class="pool-empty">
            {{ poolSearch ? '无匹配字段' : '所有字段已放置' }}
          </div>
        </div>
      </div>

      <!-- 中央：画布 -->
      <div class="canvas-area">
        <div class="canvas-wrap">
          <!-- 画布行 -->
          <div
            v-for="(row, rowIdx) in layout.rows"
            :key="row.id"
            class="canvas-row"
          >
            <!-- 行操作 -->
            <div class="row-actions">
              <NButton
                text size="tiny"
                :disabled="rowIdx === 0"
                @click="moveRow(rowIdx, -1)"
              >
                <Icon name="heroicons:chevron-up" class="w-3.5 h-3.5" />
              </NButton>
              <NButton
                text size="tiny"
                :disabled="rowIdx === layout.rows.length - 1"
                @click="moveRow(rowIdx, 1)"
              >
                <Icon name="heroicons:chevron-down" class="w-3.5 h-3.5" />
              </NButton>
              <NButton text size="tiny" type="error" @click="removeRow(rowIdx)">
                <Icon name="heroicons:x-mark" class="w-3.5 h-3.5" />
              </NButton>
            </div>

            <!-- 行单元格 -->
            <div class="row-cells" :class="`row-cells--${row.cells.length}`">
              <div
                v-for="(cell, cellIdx) in row.cells"
                :key="cellIdx"
                class="canvas-cell"
                :style="{ gridColumn: `span ${cell.span}` }"
              >
                <div class="cell-field">
                  <div class="cell-field-info">
                    <span class="cell-field-label">{{ fieldMap[cell.field]?.label ?? cell.field }}</span>
                    <code class="cell-field-key">{{ cell.field }}</code>
                    <NTag
                      v-if="fieldMap[cell.field]?.inherited"
                      size="tiny" type="info"
                    >继承</NTag>
                  </div>
                  <div class="cell-field-actions">
                    <!-- 切换 span -->
                    <NButton
                      text size="tiny"
                      :title="cell.span === 1 ? '扩展为整行' : '收缩为半行'"
                      @click="toggleSpan(rowIdx, cellIdx)"
                    >
                      <Icon
                        :name="cell.span === 1 ? 'heroicons:arrows-pointing-out' : 'heroicons:arrows-pointing-in'"
                        class="w-3.5 h-3.5"
                      />
                    </NButton>
                    <!-- 移除 -->
                    <NButton text size="tiny" type="error" @click="removeCell(rowIdx, cellIdx)">
                      <Icon name="heroicons:x-mark" class="w-3.5 h-3.5" />
                    </NButton>
                  </div>
                </div>
              </div>

              <!-- 空槽（当行有空位时显示） -->
              <div
                v-if="rowHasSlot(row)"
                class="canvas-slot"
                @dragover.prevent="onSlotDragOver(rowIdx)"
                @dragleave="dragOverRow = null"
                @drop.prevent="onSlotDrop(rowIdx)"
                :class="{ 'canvas-slot--active': dragOverRow === rowIdx }"
              >
                <Icon name="heroicons:plus" class="w-4 h-4" />
                拖入字段
              </div>
            </div>
          </div>

          <!-- 新行放置区 -->
          <div
            class="canvas-new-row"
            @dragover.prevent="onNewRowDragOver"
            @dragleave="dragOverNewRow = false"
            @drop.prevent="onNewRowDrop"
            :class="{ 'canvas-new-row--active': dragOverNewRow }"
          >
            <Icon name="heroicons:plus-circle" class="w-5 h-5" />
            拖入此处新建一行
          </div>
        </div>

        <!-- 空态提示 -->
        <div v-if="layout.rows.length === 0" class="canvas-empty">
          <Icon name="heroicons:squares-plus" class="w-10 h-10 opacity-30" />
          <p>从左侧字段库拖拽字段到下方"新建一行"区域</p>
        </div>
      </div>

      <!-- 右侧：预览 -->
      <div class="preview-panel">
        <div class="pool-title">
          <Icon name="heroicons:eye" class="w-4 h-4" />
          表单预览
        </div>
        <div class="preview-form">
          <template v-for="row in layout.rows" :key="row.id">
            <div class="preview-row">
              <div
                v-for="cell in row.cells"
                :key="cell.field"
                class="preview-cell"
                :style="{ flex: cell.span }"
              >
                <div class="preview-field-label">
                  {{ fieldMap[cell.field]?.label ?? cell.field }}
                  <span v-if="fieldMap[cell.field]?.required" class="text-red-500">*</span>
                </div>
                <div class="preview-field-input" :class="`preview-field-input--${fieldMap[cell.field]?.type}`">
                  <template v-if="fieldMap[cell.field]?.type === 'select'">
                    <span class="text-gray-400 text-xs">▼ 请选择</span>
                  </template>
                  <template v-else-if="fieldMap[cell.field]?.type === 'boolean'">
                    <span class="preview-toggle" />
                  </template>
                  <template v-else-if="fieldMap[cell.field]?.type === 'textarea'">
                    <div style="height: 48px" />
                  </template>
                  <template v-else>
                    <span class="text-gray-300 text-xs">{{ fieldMap[cell.field]?.placeholder || '请输入' }}</span>
                  </template>
                </div>
              </div>
            </div>
          </template>
          <div v-if="layout.rows.length === 0" class="text-center text-gray-300 text-sm py-8">
            暂无排版
          </div>
        </div>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRoute, useRouter } from "vue-router";
import { NButton, NInput, NTag, NSpin, useMessage } from "naive-ui";
import {
  CategoryAPI,
  type ArchiveCategory,
  type FieldDefinition,
  type FormLayout,
  type FormLayoutRow,
  type FormLayoutCell,
} from "@/api/repository";

definePageMeta({ layout: "archive", middleware: "auth" });

const route   = useRoute();
const router  = useRouter();
const message = useMessage();

const categoryId = computed(() => route.params.id as string);

// ── 数据 ──────────────────────────────────────────────────────────────────────

const loading  = ref(false);
const saving   = ref(false);
const category = ref<ArchiveCategory | null>(null);
const allFields = ref<FieldDefinition[]>([]);

const layout = ref<FormLayout>({ cols: 2, rows: [] });

/** 字段 name → 定义的快速查表 */
const fieldMap = computed(() => {
  const m: Record<string, FieldDefinition> = {};
  allFields.value.forEach((f) => { m[f.name] = f; });
  return m;
});

/** 已放置到画布的字段 name 集合 */
const placedFieldNames = computed(() => {
  const s = new Set<string>();
  layout.value.rows.forEach((row) => row.cells.forEach((c) => s.add(c.field)));
  return s;
});

/** 字段库 = 全量字段 - 已放置字段 */
const poolFields = computed(() =>
  allFields.value.filter((f) => !placedFieldNames.value.has(f.name)),
);

const poolSearch       = ref("");
const filteredPoolFields = computed(() => {
  const q = poolSearch.value.trim().toLowerCase();
  if (!q) return poolFields.value;
  return poolFields.value.filter(
    (f) => f.label.includes(q) || f.name.toLowerCase().includes(q),
  );
});

const fieldTypeOptions = [
  { label: "文本", value: "text" }, { label: "数字", value: "number" },
  { label: "日期", value: "date" }, { label: "下拉", value: "select" },
  { label: "开关", value: "boolean" }, { label: "多行文本", value: "textarea" },
];
const fieldTypeLabel = (t: string) =>
  fieldTypeOptions.find((o) => o.value === t)?.label ?? t;

// ── 加载 ──────────────────────────────────────────────────────────────────────

async function loadData() {
  loading.value = true;
  try {
    const [catRes, schemaRes, layoutRes] = await Promise.all([
      CategoryAPI.list(),
      CategoryAPI.getSchema(categoryId.value),
      CategoryAPI.getLayout(categoryId.value),
    ]);
    category.value  = catRes.data.find((c) => c.id === categoryId.value) ?? null;
    allFields.value = schemaRes.data ?? [];
    layout.value    = layoutRes.data ?? { cols: 2, rows: [] };
  } finally {
    loading.value = false;
  }
}

onMounted(loadData);

// ── 画布操作 ─────────────────────────────────────────────────────────────────

function rowHasSlot(row: FormLayoutRow): boolean {
  // 一行最多 2 个 span=1 的字段，或 1 个 span=2 的字段
  const usedSpans = row.cells.reduce((s, c) => s + c.span, 0);
  return usedSpans < 2;
}

function makeRowId() {
  return `row-${Date.now()}-${Math.random().toString(36).slice(2, 7)}`;
}

function toggleSpan(rowIdx: number, cellIdx: number) {
  const row  = layout.value.rows[rowIdx];
  if (!row) return;
  const cell = row.cells[cellIdx];
  if (!cell) return;
  if (cell.span === 1) {
    // 扩展为整行 → 如果行里还有另一个字段，把它移回字段池
    if (row.cells.length > 1) {
      row.cells.splice(cellIdx === 0 ? 1 : 0, 1);
    }
    cell.span = 2;
  } else {
    cell.span = 1;
  }
}

function removeCell(rowIdx: number, cellIdx: number) {
  const row = layout.value.rows[rowIdx];
  if (!row) return;
  row.cells.splice(cellIdx, 1);
  if (row.cells.length === 0) {
    layout.value.rows.splice(rowIdx, 1);
  }
}

function removeRow(rowIdx: number) {
  layout.value.rows.splice(rowIdx, 1);
}

function moveRow(rowIdx: number, dir: -1 | 1) {
  const rows   = layout.value.rows;
  const target = rowIdx + dir;
  if (target < 0 || target >= rows.length) return;
  const a = rows[rowIdx];
  const b = rows[target];
  if (!a || !b) return;
  rows[rowIdx] = b;
  rows[target] = a;
}

function clearLayout() {
  layout.value = { cols: 2, rows: [] };
}

// ── 拖拽逻辑 ─────────────────────────────────────────────────────────────────

const draggingField = ref<FieldDefinition | null>(null);
const dragOverRow   = ref<number | null>(null);
const dragOverNewRow = ref(false);

function onPoolDragStart(field: FieldDefinition) {
  draggingField.value = field;
}

function onSlotDragOver(rowIdx: number) {
  dragOverRow.value = rowIdx;
}

function onSlotDrop(rowIdx: number) {
  const field = draggingField.value;
  if (!field) return;
  const row = layout.value.rows[rowIdx];
  if (!row) return;
  const used = row.cells.reduce((s, c) => s + c.span, 0);
  if (used >= 2) return;
  const cell: FormLayoutCell = { field: field.name, span: 1 };
  row.cells.push(cell);
  dragOverRow.value   = null;
  draggingField.value = null;
}

function onNewRowDragOver() {
  dragOverNewRow.value = true;
}

function onNewRowDrop() {
  const field = draggingField.value;
  if (!field) return;
  const newRow: FormLayoutRow = {
    id: makeRowId(),
    cells: [{ field: field.name, span: 1 }],
  };
  layout.value.rows.push(newRow);
  dragOverNewRow.value = false;
  draggingField.value  = null;
}

// ── 保存 ─────────────────────────────────────────────────────────────────────

async function saveLayout() {
  saving.value = true;
  try {
    await CategoryAPI.updateLayout(categoryId.value, layout.value);
    message.success("排版已保存");
  } finally {
    saving.value = false;
  }
}
</script>

<style scoped>
/* ── 顶部栏 ──────────────────────────────────────────────────────────────────── */
.designer-header {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 12px 20px;
  border-bottom: 1px solid var(--n-divider-color, rgba(0,0,0,.08));
  background: var(--n-card-color, #fff);
  flex-shrink: 0;
}

/* ── 主体三栏布局 ───────────────────────────────────────────────────────────── */
.designer-body {
  display: flex;
  flex: 1;
  overflow: hidden;
  min-height: 0;
}

/* ── 字段库（左） ────────────────────────────────────────────────────────────── */
.field-pool {
  width: 220px;
  flex-shrink: 0;
  border-right: 1px solid var(--n-divider-color, rgba(0,0,0,.08));
  background: var(--n-card-color, #fff);
  display: flex;
  flex-direction: column;
  overflow: hidden;
}

.pool-title {
  display: flex;
  align-items: center;
  gap: 6px;
  font-size: 12px;
  font-weight: 600;
  color: var(--n-text-color-3, #888);
  text-transform: uppercase;
  letter-spacing: 0.04em;
  padding: 12px 14px 6px;
  flex-shrink: 0;
}

.pool-count {
  margin-left: auto;
  font-weight: 400;
  font-size: 11px;
}

.pool-search {
  padding: 4px 12px 8px;
  flex-shrink: 0;
}

.pool-list {
  flex: 1;
  overflow-y: auto;
  padding: 4px 8px 12px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.pool-field {
  border-radius: 6px;
  padding: 7px 10px;
  border: 1px solid var(--n-divider-color, rgba(0,0,0,.08));
  background: var(--n-card-color, #fff);
  cursor: grab;
  transition: box-shadow .12s, border-color .12s;
  user-select: none;
}

.pool-field:hover {
  border-color: var(--n-primary-color, #18a058);
  box-shadow: 0 2px 8px rgba(0,0,0,.06);
}

.pool-field:active {
  cursor: grabbing;
  opacity: .7;
}

.pool-field--inherited {
  background: var(--n-color-embedded, rgba(0,0,0,.02));
}

.pool-field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--n-text-color-1, #333);
}

.pool-field-meta {
  display: flex;
  align-items: center;
  gap: 4px;
  margin-top: 2px;
}

.pool-field-meta code {
  font-size: 10px;
  color: var(--n-text-color-3, #aaa);
  font-family: 'Fira Code', monospace;
}

.pool-empty {
  text-align: center;
  color: var(--n-text-color-3, #aaa);
  font-size: 12px;
  padding: 20px 0;
}

/* ── 画布（中） ──────────────────────────────────────────────────────────────── */
.canvas-area {
  flex: 1;
  overflow-y: auto;
  background: var(--n-color-embedded, #f7f8fa);
  padding: 20px;
  display: flex;
  flex-direction: column;
  gap: 0;
}

.canvas-wrap {
  display: flex;
  flex-direction: column;
  gap: 8px;
  max-width: 780px;
  margin: 0 auto;
  width: 100%;
}

/* 单行容器 */
.canvas-row {
  display: flex;
  gap: 0;
  align-items: stretch;
  background: var(--n-card-color, #fff);
  border: 1px solid var(--n-divider-color, rgba(0,0,0,.08));
  border-radius: 8px;
  overflow: hidden;
  position: relative;
}

.row-actions {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 2px;
  padding: 6px 4px;
  border-right: 1px solid var(--n-divider-color, rgba(0,0,0,.06));
  background: var(--n-color-embedded, rgba(0,0,0,.02));
  flex-shrink: 0;
}

.row-cells {
  display: grid;
  grid-template-columns: 1fr 1fr;
  flex: 1;
}

.canvas-cell {
  padding: 10px 12px;
  border-right: 1px dashed var(--n-divider-color, rgba(0,0,0,.08));
}

.canvas-cell:last-child {
  border-right: none;
}

.cell-field {
  display: flex;
  align-items: center;
  justify-content: space-between;
  gap: 8px;
}

.cell-field-info {
  display: flex;
  align-items: center;
  gap: 6px;
  flex-wrap: wrap;
  min-width: 0;
}

.cell-field-label {
  font-size: 13px;
  font-weight: 500;
  color: var(--n-text-color-1, #333);
}

.cell-field-key {
  font-size: 10px;
  color: var(--n-text-color-3, #aaa);
  font-family: 'Fira Code', monospace;
}

.cell-field-actions {
  display: flex;
  gap: 2px;
  flex-shrink: 0;
}

/* 空槽 */
.canvas-slot {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 6px;
  padding: 12px;
  color: var(--n-text-color-3, #bbb);
  font-size: 12px;
  border: 1.5px dashed var(--n-divider-color, #ddd);
  border-radius: 6px;
  margin: 8px;
  transition: border-color .15s, color .15s, background .15s;
  cursor: copy;
}

.canvas-slot--active {
  border-color: var(--n-primary-color, #18a058);
  color: var(--n-primary-color, #18a058);
  background: color-mix(in srgb, var(--n-primary-color, #18a058) 5%, transparent);
}

/* 新行放置区 */
.canvas-new-row {
  display: flex;
  align-items: center;
  justify-content: center;
  gap: 8px;
  padding: 14px;
  border: 2px dashed var(--n-divider-color, #ddd);
  border-radius: 8px;
  color: var(--n-text-color-3, #bbb);
  font-size: 13px;
  transition: border-color .15s, color .15s, background .15s;
  cursor: copy;
  margin-top: 4px;
}

.canvas-new-row--active {
  border-color: var(--n-primary-color, #18a058);
  color: var(--n-primary-color, #18a058);
  background: color-mix(in srgb, var(--n-primary-color, #18a058) 5%, transparent);
}

.canvas-empty {
  display: flex;
  flex-direction: column;
  align-items: center;
  justify-content: center;
  gap: 8px;
  color: var(--n-text-color-3, #ccc);
  font-size: 13px;
  padding: 32px 0;
}

/* ── 预览（右） ──────────────────────────────────────────────────────────────── */
.preview-panel {
  width: 260px;
  flex-shrink: 0;
  border-left: 1px solid var(--n-divider-color, rgba(0,0,0,.08));
  background: var(--n-card-color, #fff);
  overflow-y: auto;
  display: flex;
  flex-direction: column;
}

.preview-form {
  padding: 8px 14px 16px;
  display: flex;
  flex-direction: column;
  gap: 4px;
}

.preview-row {
  display: flex;
  gap: 8px;
}

.preview-cell {
  display: flex;
  flex-direction: column;
  gap: 3px;
  min-width: 0;
}

.preview-field-label {
  font-size: 11px;
  color: var(--n-text-color-2, #555);
  font-weight: 500;
}

.preview-field-input {
  border: 1px solid var(--n-divider-color, #e0e0e0);
  border-radius: 4px;
  padding: 5px 8px;
  font-size: 11px;
  background: var(--n-color-embedded, rgba(0,0,0,.02));
  min-height: 26px;
  display: flex;
  align-items: center;
}

.preview-field-input--textarea {
  align-items: flex-start;
  min-height: 48px;
}

.preview-toggle {
  display: inline-block;
  width: 26px;
  height: 14px;
  border-radius: 7px;
  background: var(--n-divider-color, #ccc);
  position: relative;
}

.preview-toggle::after {
  content: '';
  position: absolute;
  top: 2px;
  left: 2px;
  width: 10px;
  height: 10px;
  border-radius: 50%;
  background: #fff;
}
</style>
