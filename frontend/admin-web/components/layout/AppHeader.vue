<template>
  <header
    class="bg-base-100 shadow-sm border-b border-base-300 sticky top-0 z-50"
  >
    <div
      class="max-w-[1600px] mx-auto px-4 sm:px-6 lg:px-8 h-16 flex items-center justify-between"
    >
      <!-- 品牌 -->
      <div class="flex items-center gap-4">
        <NuxtLink to="/" class="flex items-center gap-3 group">
          <div
            class="flex items-center justify-center w-10 h-10 rounded-lg bg-primary text-primary-content shadow-soft group-hover:shadow-soft-hover transition-shadow"
          >
            <ArchiveBoxSolid class="w-5 h-5" />
          </div>
          <div>
            <h1 class="text-lg font-bold text-base-content leading-tight">
              智慧档案综合管理平台
            </h1>
            <p
              class="text-[10px] text-base-content/50 font-medium tracking-widest uppercase"
            >
              V2.0 Enterprise Edition
            </p>
          </div>
        </NuxtLink>
      </div>

      <!-- 搜索栏 -->
      <div class="flex-1 max-w-2xl mx-8 hidden md:block">
        <div class="relative group">
          <div
            class="absolute inset-y-0 left-0 pl-3 flex items-center pointer-events-none"
          >
            <MagnifyingGlassIcon
              class="w-5 h-5 text-base-content/40 group-focus-within:text-primary transition-colors"
            />
          </div>
          <input
            type="text"
            placeholder="搜索档案、档号或系统功能..."
            class="input input-bordered w-full pl-10 pr-12 h-10 text-sm bg-base-200/50 border-base-300 text-base-content placeholder:text-base-content/40 focus:outline-none focus:border-primary transition-all rounded-lg"
          />
          <div class="absolute inset-y-0 right-0 pr-3 flex items-center">
            <kbd class="kbd kbd-sm text-base-content/50"> ⌘K </kbd>
          </div>
        </div>
      </div>

      <!-- 右侧操作区 -->
      <HeaderActions />
    </div>
  </header>
</template>

<script setup lang="ts">
import { ArchiveBoxIcon as ArchiveBoxSolid } from "@heroicons/vue/24/solid";
import { MagnifyingGlassIcon } from "@heroicons/vue/24/outline";
import HeaderActions from "./HeaderActions.vue";
</script>
