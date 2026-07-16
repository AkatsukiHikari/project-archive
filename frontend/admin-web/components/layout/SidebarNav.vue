<template>
  <aside
    class="fixed left-0 z-40 flex flex-col"
    style="transition: width 0.3s ease, background-color 0.3s ease"
    :style="{
      top: `${top}px`,
      bottom: 0,
      width: layout.collapsed ? '64px' : '240px',
      background: layout.sidebarDark ? DARK_BG : 'var(--semi-color-bg-0)',
      borderRight: layout.sidebarDark ? 'none' : '1px solid var(--semi-color-border)',
    }"
  >
    <!-- Logo（混合布局时 Logo 在顶栏，侧栏不再重复） -->
    <div
      v-if="showLogo"
      class="flex items-center shrink-0 overflow-hidden cursor-pointer"
      style="padding: 12px 14px; height: 56px"
      title="返回平台首页"
      @click="router.push('/')"
    >
      <LogoIcon :size="28" class="shrink-0" />
      <Transition name="logo-text">
        <div v-if="!layout.collapsed" class="ml-2.5 overflow-hidden">
          <div
            class="text-[13px] font-bold leading-tight whitespace-nowrap"
            :style="{ color: layout.sidebarDark ? 'rgba(255,255,255,0.92)' : 'var(--semi-color-text-0)' }"
          >
            {{ title }}
          </div>
          <div
            class="text-[9px] tracking-widest uppercase mt-0.5"
            :style="{ color: layout.sidebarDark ? 'rgba(255,255,255,0.45)' : 'var(--semi-color-text-2)' }"
          >
            {{ subtitle }}
          </div>
        </div>
      </Transition>
    </div>

    <!-- 菜单 -->
    <div class="flex-1 overflow-y-auto custom-scrollbar" :class="showLogo ? '' : 'pt-2'">
      <NMenu
        :options="options"
        :collapsed="layout.collapsed"
        :collapsed-width="64"
        :collapsed-icon-size="20"
        :indent="18"
        :inverted="layout.sidebarDark"
        :value="selectedKey"
        :expanded-keys="expandedKeys"
        @update:value="(k: string) => emit('select', k)"
        @update:expanded-keys="expandedKeys = $event"
      />
    </div>

    <!-- 返回主界面 -->
    <div v-if="showBackHome" class="shrink-0 border-t" :style="{ borderColor: dividerColor }">
      <button
        class="w-full flex items-center gap-2 h-10 px-4 transition-colors cursor-pointer"
        :class="[layout.collapsed ? 'justify-center' : 'justify-start', hoverClass]"
        @click="router.push('/')"
      >
        <Icon name="heroicons:home" class="w-4 h-4 shrink-0" :style="{ color: mutedColor }" />
        <span v-if="!layout.collapsed" class="text-xs" :style="{ color: mutedColor }">返回主界面</span>
      </button>
    </div>

    <!-- 折叠按钮 -->
    <div class="shrink-0 border-t" :style="{ borderColor: dividerColor }">
      <button
        class="w-full flex items-center justify-center h-10 transition-colors cursor-pointer"
        :class="hoverClass"
        @click="layout.toggleCollapsed()"
      >
        <Icon
          :name="layout.collapsed ? 'heroicons:chevron-right' : 'heroicons:chevron-left'"
          class="w-4 h-4"
          :style="{ color: mutedColor }"
        />
      </button>
    </div>
  </aside>
</template>

<script setup lang="ts">
import { computed, ref, watch } from "vue";
import { useRouter } from "vue-router";
import { NMenu, type MenuOption } from "naive-ui";
import LogoIcon from "@/components/common/LogoIcon.vue";
import { useLayoutStore } from "@/stores/layout";

const DARK_BG = "#1b2233";

const props = withDefaults(
  defineProps<{
    options: MenuOption[];
    selectedKey: string;
    title?: string;
    subtitle?: string;
    /** 顶部偏移：混合布局下侧栏从顶栏下方开始 */
    top?: number;
    showLogo?: boolean;
    showBackHome?: boolean;
  }>(),
  { title: "", subtitle: "", top: 0, showLogo: true, showBackHome: false },
);

const emit = defineEmits<{ (e: "select", key: string): void }>();

const router = useRouter();
const layout = useLayoutStore();

const dividerColor = computed(() =>
  layout.sidebarDark ? "rgba(255,255,255,0.09)" : "var(--semi-color-border)",
);
const mutedColor = computed(() =>
  layout.sidebarDark ? "rgba(255,255,255,0.55)" : "var(--semi-color-text-2)",
);
const hoverClass = computed(() =>
  layout.sidebarDark ? "hover:bg-white/10" : "hover:bg-[var(--semi-color-fill-0)]",
);

// 首次拿到菜单时默认展开全部一级分组；混合布局切换栏目时也重新展开
const expandedKeys = ref<string[]>([]);
watch(
  () => props.options,
  (opts) => {
    expandedKeys.value = opts
      .filter((o) => Array.isArray(o.children) && o.children.length > 0)
      .map((o) => String(o.key));
  },
  { immediate: true },
);
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar { width: 4px; }
.custom-scrollbar::-webkit-scrollbar-track { background: transparent; }
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: var(--semi-color-fill-1);
  border-radius: 20px;
}

.logo-text-enter-active,
.logo-text-leave-active { transition: opacity 0.2s, transform 0.2s; }
.logo-text-enter-from,
.logo-text-leave-to { opacity: 0; transform: translateX(-6px); }
</style>
