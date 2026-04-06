<template>
  <div
    class="tabs-bar flex items-center h-10 bg-[var(--semi-color-bg-0)] border-b border-[var(--semi-color-border)] select-none"
    @click="hideMenu"
  >
    <!-- Tab List (horizontally scrollable) -->
    <div
      ref="scrollRef"
      class="tabs-scroll flex-1 flex items-stretch h-full overflow-x-auto overflow-y-hidden"
    >
      <div
        v-for="tab in tabsStore.tabs"
        :key="tab.path"
        :ref="(el) => setTabRef(tab.path, el as HTMLElement | null)"
        class="tab-item flex items-center gap-1.5 px-3 h-full cursor-pointer whitespace-nowrap border-b-2 transition-all duration-150 shrink-0 text-xs font-medium"
        :class="isActive(tab.path) ? 'tab-active' : 'tab-inactive'"
        @click.stop="onTabClick(tab.path)"
        @contextmenu.prevent="(e) => onContextMenu(e, tab)"
      >
        <!-- Home icon for pinned home tab -->
        <svg
          v-if="!tab.closable"
          class="w-3.5 h-3.5 shrink-0"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <path d="M3 9l9-7 9 7v11a2 2 0 0 1-2 2H5a2 2 0 0 1-2-2z" />
          <polyline points="9 22 9 12 15 12 15 22" />
        </svg>

        <span>{{ tab.title }}</span>

        <!-- Close button for closable tabs -->
        <button
          v-if="tab.closable"
          class="tab-close flex items-center justify-center w-4 h-4 rounded-full transition-colors shrink-0"
          :title="`关闭 ${tab.title}`"
          @click.stop="onClose(tab.path)"
        >
          <svg
            class="w-2.5 h-2.5"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2.5"
            stroke-linecap="round"
          >
            <line x1="18" y1="6" x2="6" y2="18" />
            <line x1="6" y1="6" x2="18" y2="18" />
          </svg>
        </button>
      </div>
    </div>

    <!-- Right action buttons -->
    <div
      class="flex items-center shrink-0 border-l border-[var(--semi-color-border)] h-full"
    >
      <button
        class="icon-btn px-3 h-full flex items-center transition-colors"
        title="刷新当前页"
        @click.stop="onRefresh"
      >
        <svg
          class="w-3.5 h-3.5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
          stroke-linejoin="round"
        >
          <polyline points="23 4 23 10 17 10" />
          <polyline points="1 20 1 14 7 14" />
          <path
            d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"
          />
        </svg>
      </button>

      <button
        ref="moreBtn"
        class="icon-btn px-3 h-full flex items-center transition-colors"
        title="更多操作"
        @click.stop="onMoreClick"
      >
        <svg
          class="w-3.5 h-3.5"
          viewBox="0 0 24 24"
          fill="none"
          stroke="currentColor"
          stroke-width="2"
          stroke-linecap="round"
        >
          <circle cx="12" cy="5" r="1" fill="currentColor" />
          <circle cx="12" cy="12" r="1" fill="currentColor" />
          <circle cx="12" cy="19" r="1" fill="currentColor" />
        </svg>
      </button>
    </div>

    <!-- Context Menu (teleported to body to escape stacking context) -->
    <Teleport to="body">
      <div
        v-if="menu.visible"
        class="ctx-menu fixed z-[9999] min-w-[144px] rounded-lg shadow-xl py-1"
        :style="{ top: menu.y + 'px', left: menu.x + 'px' }"
        @click.stop
        @contextmenu.stop.prevent
      >
        <button
          v-for="item in menuItems"
          :key="item.key"
          class="ctx-item w-full text-left px-3 py-2 text-xs flex items-center gap-2 transition-colors"
          :class="item.disabled ? 'opacity-40 cursor-not-allowed' : 'cursor-pointer'"
          :disabled="item.disabled"
          @click="!item.disabled && (item.action(), hideMenu())"
        >
          <svg
            class="w-3.5 h-3.5 shrink-0"
            viewBox="0 0 24 24"
            fill="none"
            stroke="currentColor"
            stroke-width="2"
            stroke-linecap="round"
            stroke-linejoin="round"
            v-html="item.iconPath"
          />
          {{ item.label }}
        </button>
      </div>
    </Teleport>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onUnmounted } from "vue";
import { useRouter } from "vue-router";
import { useTabsRouteStore, type TabItem } from "@/stores/tabsRoute";

const router = useRouter();
const tabsStore = useTabsRouteStore();

// ─── Tab element refs for scroll-into-view ────────────────────────────────
const scrollRef = ref<HTMLElement | null>(null);
const tabRefs = ref<Map<string, HTMLElement>>(new Map());

function setTabRef(path: string, el: HTMLElement | null) {
  if (el) {
    tabRefs.value.set(path, el);
  } else {
    tabRefs.value.delete(path);
  }
}

function isActive(path: string) {
  return path === tabsStore.activeTab;
}

watch(
  () => tabsStore.activeTab,
  async (path) => {
    await nextTick();
    const el = tabRefs.value.get(path);
    el?.scrollIntoView({ behavior: "smooth", block: "nearest", inline: "nearest" });
  },
);

// ─── Tab actions ───────────────────────────────────────────────────────────
function onTabClick(path: string) {
  hideMenu();
  tabsStore.setActive(path);
  router.push(path);
}

function onClose(path: string) {
  hideMenu();
  const redirectTo = tabsStore.closeTab(path);
  if (redirectTo) {
    router.push(redirectTo);
  }
}

function onRefresh() {
  hideMenu();
  router.go(0);
}

// ─── Context menu ─────────────────────────────────────────────────────────
const moreBtn = ref<HTMLElement | null>(null);

const menu = ref({
  visible: false,
  x: 0,
  y: 0,
  tab: null as TabItem | null,
});

const menuItems = computed(() => {
  const tab = menu.value.tab;
  if (!tab) return [];

  const idx = tabsStore.tabs.findIndex((t) => t.path === tab.path);
  const isActiveTab = tab.path === tabsStore.activeTab;
  const hasRight = tabsStore.tabs.slice(idx + 1).some((t) => t.closable);
  const hasOthers = tabsStore.tabs.some(
    (t) => t.closable && t.path !== tab.path,
  );
  const hasAny = tabsStore.tabs.some((t) => t.closable);

  return [
    {
      key: "refresh",
      label: "刷新当前页",
      disabled: !isActiveTab,
      iconPath: `<polyline points="23 4 23 10 17 10"/><polyline points="1 20 1 14 7 14"/><path d="M3.51 9a9 9 0 0 1 14.85-3.36L23 10M1 14l4.64 4.36A9 9 0 0 0 20.49 15"/>`,
      action: onRefresh,
    },
    {
      key: "close",
      label: "关闭当前",
      disabled: !tab.closable,
      iconPath: `<line x1="18" y1="6" x2="6" y2="18"/><line x1="6" y1="6" x2="18" y2="18"/>`,
      action: () => onClose(tab.path),
    },
    {
      key: "close-right",
      label: "关闭右侧",
      disabled: !hasRight,
      iconPath: `<polyline points="9 18 15 12 9 6"/>`,
      action: () => {
        tabsStore.closeRight(tab.path);
        if (!tabsStore.tabs.find((t) => t.path === router.currentRoute.value.path)) {
          router.push(tabsStore.activeTab);
        }
      },
    },
    {
      key: "close-others",
      label: "关闭其他",
      disabled: !hasOthers,
      iconPath: `<circle cx="12" cy="12" r="10"/><line x1="15" y1="9" x2="9" y2="15"/><line x1="9" y1="9" x2="15" y2="15"/>`,
      action: () => {
        tabsStore.closeOthers(tab.path);
        router.push(tab.path);
      },
    },
    {
      key: "close-all",
      label: "关闭全部",
      disabled: !hasAny,
      iconPath: `<polyline points="3 6 5 6 21 6"/><path d="M19 6v14a2 2 0 0 1-2 2H7a2 2 0 0 1-2-2V6m3 0V4a1 1 0 0 1 1-1h4a1 1 0 0 1 1 1v2"/>`,
      action: () => {
        tabsStore.closeAll();
        router.push(tabsStore.activeTab);
      },
    },
  ];
});

function showMenu(x: number, y: number, tab: TabItem) {
  // Prevent menu from overflowing viewport
  const safeX = Math.min(x, window.innerWidth - 160);
  const safeY = Math.min(y, window.innerHeight - 220);
  menu.value = { visible: true, x: safeX, y: safeY, tab };
}

function onContextMenu(e: MouseEvent, tab: TabItem) {
  showMenu(e.clientX, e.clientY, tab);
}

function onMoreClick() {
  const activetab = tabsStore.tabs.find((t) => t.path === tabsStore.activeTab);
  if (!activetab || !moreBtn.value) return;
  const rect = moreBtn.value.getBoundingClientRect();
  showMenu(rect.right - 160, rect.bottom + 4, activetab);
}

function hideMenu() {
  menu.value.visible = false;
}

// Global click to close menu
function onGlobalClick() {
  if (menu.value.visible) hideMenu();
}

if (typeof document !== "undefined") {
  document.addEventListener("click", onGlobalClick, true);
  document.addEventListener("contextmenu", onGlobalClick, true);
}

onUnmounted(() => {
  if (typeof document !== "undefined") {
    document.removeEventListener("click", onGlobalClick, true);
    document.removeEventListener("contextmenu", onGlobalClick, true);
  }
});
</script>

<style scoped>
/* 隐藏滚动条，但保留滚动功能 */
.tabs-scroll {
  scrollbar-width: none;
  -ms-overflow-style: none;
}
.tabs-scroll::-webkit-scrollbar {
  display: none;
}

/* Active tab */
.tab-active {
  border-color: var(--semi-color-primary);
  color: var(--semi-color-primary);
  background-color: var(--semi-color-primary-light-default);
}

/* Inactive tab */
.tab-inactive {
  border-color: transparent;
  color: var(--semi-color-text-1);
}
.tab-inactive:hover {
  background-color: var(--semi-color-fill-0);
  color: var(--semi-color-text-0);
}

/* Close button - only fully visible on hover */
.tab-close {
  opacity: 0.4;
}
.tab-item:hover .tab-close,
.tab-active .tab-close {
  opacity: 1;
}
.tab-close:hover {
  background-color: var(--semi-color-fill-2);
}

/* Right icon buttons */
.icon-btn {
  color: var(--semi-color-text-2);
}
.icon-btn:hover {
  background-color: var(--semi-color-fill-0);
  color: var(--semi-color-text-0);
}

/* Context menu */
.ctx-menu {
  background-color: var(--semi-color-bg-2);
  border: 1px solid var(--semi-color-border);
  animation: menu-in 0.1s ease-out;
}

.ctx-item {
  color: var(--semi-color-text-0);
}
.ctx-item:not(:disabled):hover {
  background-color: var(--semi-color-fill-0);
}

@keyframes menu-in {
  from {
    opacity: 0;
    transform: translateY(-4px) scale(0.98);
  }
  to {
    opacity: 1;
    transform: translateY(0) scale(1);
  }
}
</style>
