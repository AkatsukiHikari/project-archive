<template>
  <NPopover trigger="click" placement="bottom-end" :show-arrow="false" style="padding: 12px">
    <template #trigger>
      <button class="btn btn-ghost btn-circle btn-sm" title="切换布局">
        <Icon name="heroicons:squares-2x2" class="w-5 h-5" />
      </button>
    </template>

    <div class="flex flex-col gap-3 w-56">
      <div class="text-xs font-semibold px-0.5" style="color: var(--semi-color-text-2)">界面布局</div>

      <!-- 三种布局缩略图 -->
      <div class="grid grid-cols-3 gap-2.5">
        <button
          v-for="m in MODES"
          :key="m.value"
          class="flex flex-col items-center gap-1.5 cursor-pointer bg-transparent border-none p-0 group"
          :title="m.label"
          @click="layout.setMode(m.value)"
        >
          <div
            class="w-16 h-12 rounded-md overflow-hidden relative transition-shadow"
            :style="{
              background: 'var(--semi-color-fill-0)',
              boxShadow: layout.mode === m.value
                ? '0 0 0 2px oklch(var(--p))'
                : '0 0 0 1px var(--semi-color-border)',
            }"
          >
            <!-- sidebar：左侧深条 + 顶浅条 -->
            <template v-if="m.value === 'sidebar'">
              <div class="absolute inset-y-0 left-0 w-4 rounded-l-md" style="background: #344054" />
              <div class="absolute top-0 left-4 right-0 h-2.5" style="background: var(--semi-color-bg-0); border-bottom: 1px solid var(--semi-color-border)" />
            </template>
            <!-- topnav：顶深条 -->
            <template v-else-if="m.value === 'topnav'">
              <div class="absolute top-0 inset-x-0 h-3 rounded-t-md" style="background: #344054" />
            </template>
            <!-- mix：顶深条 + 左浅条 -->
            <template v-else>
              <div class="absolute top-0 inset-x-0 h-3 rounded-t-md" style="background: #344054" />
              <div class="absolute left-0 top-3 bottom-0 w-4 rounded-bl-md" style="background: var(--semi-color-bg-0); border-right: 1px solid var(--semi-color-border)" />
            </template>
          </div>
          <span
            class="text-[11px] leading-none"
            :style="{ color: layout.mode === m.value ? 'oklch(var(--p))' : 'var(--semi-color-text-2)' }"
          >{{ m.label }}</span>
        </button>
      </div>

      <!-- 侧栏深色 -->
      <div class="flex items-center justify-between pt-2 border-t" style="border-color: var(--semi-color-border)">
        <span
          class="text-[12.5px]"
          :style="{ color: layout.mode === 'topnav' ? 'var(--semi-color-text-3)' : 'var(--semi-color-text-1)' }"
        >侧栏深色</span>
        <NSwitch
          size="small"
          :value="layout.sidebarDark"
          :disabled="layout.mode === 'topnav'"
          @update:value="layout.setSidebarDark"
        />
      </div>
    </div>
  </NPopover>
</template>

<script setup lang="ts">
import { NPopover, NSwitch } from "naive-ui";
import { useLayoutStore, type LayoutMode } from "@/stores/layout";

const layout = useLayoutStore();

const MODES: { value: LayoutMode; label: string }[] = [
  { value: "sidebar", label: "侧边" },
  { value: "topnav", label: "顶部" },
  { value: "mix", label: "混合" },
];
</script>
