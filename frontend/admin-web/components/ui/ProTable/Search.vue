<template>
  <div class="px-4 pt-4 border-b border-base-content/10 bg-base-200/30">

    <div class="grid grid-cols-3 gap-x-4 gap-y-3">
      <template v-for="(col, idx) in columns" :key="col.key">
        <div v-show="expanded || idx < threshold" class="flex flex-col gap-1 min-w-0">
          <label class="text-[11px] font-medium opacity-50 truncate">
            {{ col.search.label || col.title }}
          </label>
          <NInput
            v-if="!col.search.type || col.search.type === 'text'"
            v-model:value="draft[String(col.key)]"
            size="small"
            :placeholder="col.search.placeholder || `请输入${col.title}`"
            clearable
            @keydown.enter="onSearch"
          />
          <NSelect
            v-else-if="col.search.type === 'select'"
            v-model:value="draft[String(col.key)]"
            :options="col.search.options"
            size="small"
            :placeholder="col.search.placeholder || `请选择${col.title}`"
            clearable
          />
        </div>
      </template>
    </div>

    <div class="flex items-center gap-2 py-3">
      <NButton
        v-if="columns.length > threshold"
        text
        size="small"
        class="opacity-50 hover:opacity-100"
        @click="expanded = !expanded"
      >
        <template #icon>
          <Icon
            :name="expanded ? 'heroicons:chevron-up' : 'heroicons:chevron-down'"
            class="w-3.5 h-3.5"
          />
        </template>
        {{ expanded ? '收起' : '展开' }}
      </NButton>
      <div class="flex-1" />
      <NButton size="small" @click="onReset">重置</NButton>
      <NButton type="primary" size="small" @click="onSearch">查询</NButton>
    </div>
  </div>
</template>

<script setup lang="ts">
import { reactive, ref } from "vue";
import { NButton, NInput, NSelect } from "naive-ui";

export interface ProColumnSearch {
  label?: string;
  placeholder?: string;
  type?: "text" | "select";
  options?: Array<{ label: string; value: string }>;
}

export interface SearchableColumn {
  key: string | number;
  title?: string;
  search: ProColumnSearch;
}

const props = withDefaults(
  defineProps<{
    columns: SearchableColumn[];
    threshold?: number;
  }>(),
  { threshold: 3 },
);

const emit = defineEmits<{
  (e: "search", values: Record<string, string>): void;
  (e: "reset"): void;
}>();

const expanded = ref(false);
const draft = reactive<Record<string, string>>({});

function onSearch() {
  emit("search", { ...draft });
}

function onReset() {
  for (const col of props.columns) {
    draft[String(col.key)] = "";
  }
  emit("reset");
}
</script>
