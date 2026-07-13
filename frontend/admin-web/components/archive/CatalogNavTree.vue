<template>
  <!-- 目录导航：门类 → 全宗号 → 年度，逐层点选过滤 -->
  <div
    v-if="open"
    class="pro-card p-3 flex flex-col gap-2 shrink-0 min-h-0"
    style="width: 248px"
  >
    <div class="flex items-center justify-between">
      <span class="text-[13px] font-medium" style="color:var(--semi-color-text-0)">目录导航</span>
      <button class="bg-transparent border-none cursor-pointer p-0.5" style="color:var(--semi-color-text-3)" title="收起" @click="open = false">
        <Icon name="heroicons:chevron-double-left" class="w-4 h-4" />
      </button>
    </div>
    <p class="text-[11px] m-0" style="color:var(--semi-color-text-3)">门类 / 全宗号 / 年度 逐层点选</p>
    <div class="flex-1 overflow-auto min-h-0">
      <NTree
        block-line
        selectable
        expand-on-click
        key-field="key"
        label-field="label"
        :data="navData"
        :on-load="onLoadNav"
        :selected-keys="selectedKeys"
        @update:selected-keys="onSelect"
      />
    </div>
    <NButton v-if="scopeLabel" size="tiny" tertiary block @click="clear">
      <template #icon><Icon name="heroicons:x-mark" class="w-3.5 h-3.5" /></template>
      清除目录筛选
    </NButton>
  </div>

  <button
    v-else
    class="pro-card shrink-0 flex flex-col items-center gap-2 py-3 cursor-pointer bg-transparent"
    style="width: 36px; color:var(--semi-color-text-2)"
    title="展开目录导航"
    @click="open = true"
  >
    <Icon name="heroicons:bars-3" class="w-4 h-4" />
    <span class="text-[11px]" style="writing-mode:vertical-rl">目录导航</span>
  </button>
</template>

<script setup lang="ts">
import { onMounted, ref, watch } from "vue";
import { NButton, NTree } from "naive-ui";
import type { TreeOption } from "naive-ui";
import { ArchiveAPI } from "@/api/repository";

export interface CatalogNavScope {
  category_id?: string;
  fonds_id?: string;
  ND_from?: number;
  ND_to?: number;
  label: string;
}

const emit = defineEmits<{
  (e: "select", scope: CatalogNavScope): void;
  (e: "clear"): void;
}>();

const props = withDefaults(
  defineProps<{ defaultOpen?: boolean; source?: "staging" | "formal" | "all" }>(),
  { defaultOpen: true, source: "staging" },
);

const open = ref(true);
const navData = ref<TreeOption[]>([]);
const selectedKeys = ref<string[]>([]);
const scopeLabel = ref("");

async function loadRoot() {
  const res = await ArchiveAPI.navCategories(props.source);
  navData.value = (res.data ?? []).map((c) => ({
    key: `c:${c.category_id}`,
    label: `${c.name}（${c.count}）`,
    isLeaf: false,
    meta: { level: "category", category_id: c.category_id, name: c.name },
  } as TreeOption));
}

async function onLoadNav(node: TreeOption): Promise<void> {
  const meta = (node.meta ?? {}) as Record<string, string>;
  if (meta.level === "category") {
    const res = await ArchiveAPI.navFonds(meta.category_id, props.source);
    node.children = (res.data ?? []).map((f) => ({
      key: `f:${meta.category_id}:${f.fonds_id}`,
      label: `${f.qzh}（${f.count}）`,
      isLeaf: false,
      meta: { level: "fonds", category_id: meta.category_id, fonds_id: f.fonds_id, qzh: f.qzh, name: meta.name },
    } as TreeOption));
  } else if (meta.level === "fonds") {
    const res = await ArchiveAPI.navYears(meta.category_id, meta.fonds_id, props.source);
    node.children = (res.data ?? []).map((y) => ({
      key: `y:${meta.category_id}:${meta.fonds_id}:${y.year}`,
      label: `${y.year} 年（${y.count}）`,
      isLeaf: true,
      meta: { level: "year", category_id: meta.category_id, fonds_id: meta.fonds_id, year: y.year, qzh: meta.qzh, name: meta.name },
    } as TreeOption));
  }
}

function onSelect(keys: string[], _opt: unknown, extra: { node: TreeOption | null }) {
  selectedKeys.value = keys;
  const node = extra.node;
  if (!node) return;
  const meta = (node.meta ?? {}) as Record<string, string | number>;
  const scope: CatalogNavScope = {
    category_id: String(meta.category_id),
    fonds_id: meta.fonds_id ? String(meta.fonds_id) : undefined,
    label: "",
  };
  if (meta.level === "year") {
    scope.ND_from = Number(meta.year);
    scope.ND_to = Number(meta.year);
    scope.label = `${meta.name} / ${meta.qzh} / ${meta.year}年`;
  } else if (meta.level === "fonds") {
    scope.label = `${meta.name} / ${meta.qzh}`;
  } else {
    scope.label = String(meta.name);
  }
  scopeLabel.value = scope.label;
  emit("select", scope);
}

function clear() {
  selectedKeys.value = [];
  scopeLabel.value = "";
  emit("clear");
}

defineExpose({ clear });
onMounted(loadRoot);

// 库切换（智能校对页 全部/暂存/正式）：清空选中并按新口径重载计数
watch(
  () => props.source,
  () => {
    selectedKeys.value = [];
    scopeLabel.value = "";
    navData.value = [];
    loadRoot();
  },
);
</script>
