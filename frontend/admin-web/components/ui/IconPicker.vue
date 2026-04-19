<template>
  <NPopover
    v-model:show="open"
    trigger="click"
    placement="bottom-start"
    :width="320"
    raw
    style="padding: 0"
  >
    <!-- 触发按钮 -->
    <template #trigger>
      <div
        class="flex items-center gap-2 px-3 h-[34px] rounded cursor-pointer border transition-colors"
        :style="{
          borderColor: open ? 'var(--semi-color-primary)' : 'var(--semi-color-border)',
          background: 'var(--semi-color-bg-0)',
        }"
      >
        <component
          :is="resolvedIcon"
          v-if="resolvedIcon"
          class="w-4 h-4 shrink-0"
          style="color: var(--semi-color-text-1)"
        />
        <span
          v-else
          class="w-4 h-4 shrink-0 rounded-full border-2 border-dashed"
          style="border-color: var(--semi-color-text-2)"
        />
        <span
          class="text-[13px] flex-1 truncate"
          :style="{ color: modelValue ? 'var(--semi-color-text-0)' : 'var(--semi-color-text-2)' }"
        >
          {{ modelValue || '点击选择图标' }}
        </span>
        <XMarkIcon
          v-if="modelValue"
          class="w-3.5 h-3.5 shrink-0 opacity-40 hover:opacity-80 transition-opacity"
          style="color: var(--semi-color-text-1)"
          @click.stop="clear"
        />
      </div>
    </template>

    <!-- 弹出面板 -->
    <div
      class="flex flex-col"
      style="
        background: var(--semi-color-bg-0);
        border: 1px solid var(--semi-color-border);
        border-radius: 6px;
        overflow: hidden;
      "
    >
      <!-- 搜索栏 -->
      <div class="p-2 border-b" style="border-color: var(--semi-color-border)">
        <NInput
          v-model:value="query"
          size="small"
          placeholder="搜索图标…"
          clearable
        >
          <template #prefix>
            <MagnifyingGlassIcon class="w-3.5 h-3.5" />
          </template>
        </NInput>
      </div>

      <!-- 图标网格 -->
      <div class="overflow-y-auto p-1.5" style="max-height: 280px">
        <div v-if="filtered.length === 0" class="py-6 text-center text-[12px]" style="color: var(--semi-color-text-2)">
          没有匹配的图标
        </div>
        <div v-else class="grid grid-cols-8 gap-0.5">
          <NTooltip
            v-for="name in filtered"
            :key="name"
            placement="top"
            :delay="600"
          >
            <template #trigger>
              <button
                class="icon-btn flex items-center justify-center w-8 h-8 rounded transition-colors cursor-pointer"
                :class="{ 'icon-btn--active': selected === `heroicons:${name}` }"
                @click="select(name)"
              >
                <component :is="iconMap[name]" class="w-4 h-4" />
              </button>
            </template>
            {{ name }}
          </NTooltip>
        </div>
      </div>
    </div>
  </NPopover>
</template>

<script setup lang="ts">
import { ref, computed, shallowRef, onMounted } from "vue";
import { NPopover, NInput, NTooltip } from "naive-ui";
import * as HeroIcons from "@heroicons/vue/24/outline";
import { MagnifyingGlassIcon, XMarkIcon } from "@heroicons/vue/24/outline";
import type { Component } from "vue";

const props = defineProps<{ modelValue: string }>();
const emit = defineEmits<{ "update:modelValue": [v: string] }>();

const open = ref(false);
const query = ref("");
const selected = computed(() => props.modelValue);

// ── 全图标 name → Component 映射 ─────────────────────────────────────────────
// pascalCase → kebab-case 转换（与 seed.py 保持一致）
function toKebab(name: string): string {
  return name
    .replace(/([A-Z])/g, (_m, c, i) => (i > 0 ? "-" : "") + c.toLowerCase())
    .replace(/^-/, "");
}

const iconMap = shallowRef<Record<string, Component>>({});
const allNames = ref<string[]>([]);

onMounted(() => {
  const map: Record<string, Component> = {};
  const names: string[] = [];
  for (const [key, comp] of Object.entries(HeroIcons)) {
    if (!key.endsWith("Icon")) continue;
    const kebab = toKebab(key.replace(/Icon$/, ""));
    map[kebab] = comp as Component;
    names.push(kebab);
  }
  iconMap.value = map;
  allNames.value = names.sort();
});

// ── 过滤 ──────────────────────────────────────────────────────────────────────
const filtered = computed(() => {
  const q = query.value.trim().toLowerCase();
  if (!q) return allNames.value;
  return allNames.value.filter((n) => n.includes(q));
});

// ── 当前图标组件 ──────────────────────────────────────────────────────────────
const resolvedIcon = computed<Component | undefined>(() => {
  if (!props.modelValue) return undefined;
  const name = props.modelValue.startsWith("heroicons:")
    ? props.modelValue.slice(10)
    : props.modelValue;
  return iconMap.value[name];
});

// ── 操作 ──────────────────────────────────────────────────────────────────────
function select(name: string) {
  emit("update:modelValue", `heroicons:${name}`);
  open.value = false;
  query.value = "";
}

function clear() {
  emit("update:modelValue", "");
}
</script>

<style scoped>
.icon-btn {
  color: var(--semi-color-text-2);
  background: transparent;
}
.icon-btn:hover {
  background: var(--semi-color-fill-1);
  color: var(--semi-color-text-0);
}
.icon-btn--active {
  background: var(--semi-color-primary) !important;
  color: #fff !important;
}
</style>
