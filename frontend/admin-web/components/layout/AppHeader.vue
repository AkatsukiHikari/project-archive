<template>
  <header
    class="bg-[var(--semi-color-bg-0)] border-b border-[var(--semi-color-border)] sticky top-0 z-50"
    style="box-shadow: 0 1px 4px 0 rgba(0,0,0,0.06);"
  >
    <div
      class="px-6 h-16 flex items-center justify-between"
    >
      <!-- 品牌 Logo -->
      <NuxtLink to="/" class="flex items-center gap-3 shrink-0 group" style="text-decoration: none;">
        <LogoIcon :size="38" />
        <div class="leading-tight">
          <div class="text-[15px] font-bold" style="color: var(--semi-color-text-0);">
            智慧档案综合管理平台
          </div>
          <div class="text-[10px] tracking-widest uppercase" style="color: var(--semi-color-text-2);">
            V2.0 Enterprise Edition
          </div>
        </div>
      </NuxtLink>

      <!-- 全局搜索 -->
      <div class="flex-1 max-w-2xl mx-8 hidden md:block">
        <div class="relative group">
          <div class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none">
            <MagnifyingGlassIcon
              class="w-4 h-4 transition-colors"
              style="color: var(--semi-color-text-2);"
            />
          </div>
          <input
            type="text"
            placeholder="搜索档案、档号或系统功能..."
            class="w-full h-9 pl-9 pr-12 text-sm rounded-lg border transition-all outline-none"
            style="
              background: var(--semi-color-fill-0);
              border-color: var(--semi-color-border);
              color: var(--semi-color-text-0);
            "
          />
          <div class="absolute inset-y-0 right-0 pr-3 flex items-center pointer-events-none">
            <span
              class="text-[10px] px-1.5 py-0.5 rounded font-mono"
              style="background: var(--semi-color-fill-1); color: var(--semi-color-text-2);"
            >⌘K</span>
          </div>
        </div>
      </div>

      <!-- 右侧操作区 -->
      <HeaderActions />
    </div>
  </header>
</template>

<script setup lang="ts">
import { MagnifyingGlassIcon } from "@heroicons/vue/24/outline";
import LogoIcon from "@/components/common/LogoIcon.vue";
import HeaderActions from "./HeaderActions.vue";
</script>
