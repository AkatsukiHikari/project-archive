<template>
  <Layout class="min-h-screen bg-[var(--semi-color-bg-0)]">
    <!-- Sidebar -->
    <LayoutSider
      class="bg-[var(--semi-color-bg-0)] border-r border-[var(--semi-color-border)] shadow-sm z-40 transition-all duration-300"
      :style="{
        position: 'fixed',
        top: 0,
        left: 0,
        height: '100vh',
        width: isCollapsed ? '60px' : '240px',
      }"
    >
      <Nav
        :default-open-keys="['platform-group', 'security-group']"
        :selected-keys="[currentRoutePath]"
        class="h-full overflow-y-auto w-full custom-scrollbar"
        :items="navItems"
        :header="{
          style: {
            padding: '14px 10px',
            display: 'flex',
            justifyContent: 'center',
          },
          logo: h(LogoIcon, { size: 34 }),
          text: h(
            'div',
            { style: 'padding-left: 4px; line-height: 1.25;' },
            [
              h('div', { style: 'font-size: 14px; font-weight: 700; color: var(--semi-color-text-0); white-space: nowrap;' }, '智慧档案平台'),
              h('div', { style: 'font-size: 10px; letter-spacing: 0.08em; text-transform: uppercase; color: var(--semi-color-text-2); margin-top: 1px;' }, 'SAMS · Enterprise'),
            ],
          ),
        }"
        :footer="{ collapseButton: true }"
        @collapse-change="onCollapseChange"
        @select="onSelect"
      />
    </LayoutSider>

    <Layout
      class="flex flex-col min-h-screen bg-[var(--semi-color-bg-1)] transition-all duration-300"
      :style="{
        marginLeft: isCollapsed ? '60px' : '240px',
        paddingTop: '104px',
      }"
    >
      <!-- Fixed top bar: SystemHeader + TabsBar -->
      <div
        :style="{
          position: 'fixed',
          top: 0,
          right: 0,
          left: isCollapsed ? '60px' : '240px',
          zIndex: 30,
          transition: 'left 0.3s',
        }"
      >
        <SystemHeader />
        <TabsBar />
      </div>

      <LayoutContent class="p-6 flex-1 w-full">
        <slot />
      </LayoutContent>

      <LayoutFooter class="shrink-0">
        <AppFooter />
      </LayoutFooter>
    </Layout>
  </Layout>
</template>

<script setup lang="ts">
import { ref, computed, watch, h } from "vue";
import { useRouter, useRoute } from "vue-router";
import {
  Layout,
  LayoutSider,
  LayoutFooter,
  LayoutContent,
  Nav,
} from "@kousum/semi-ui-vue";
import * as Icons from "@kousum/semi-icons-vue";
import * as LabIcons from "@kousum/semi-icons-lab-vue";
import SystemHeader from "@/components/layout/SystemHeader.vue";
import TabsBar from "@/components/layout/TabsBar.vue";
import AppFooter from "@/components/layout/AppFooter.vue";
import LogoIcon from "@/components/common/LogoIcon.vue";
import { useUserStore } from "@/stores/user";
import { useTabsRouteStore } from "@/stores/tabsRoute";

const router = useRouter();
const route = useRoute();
const userStore = useUserStore();
const tabsStore = useTabsRouteStore();

// ─── Auto-add tab on route change ─────────────────────────────────────────
watch(
  () => route.path,
  (path) => {
    if (!path.startsWith("/admin")) return;
    // Derive tab title from route meta breadcrumb (last item) or fallback
    const breadcrumbs = route.meta.breadcrumb as
      | { name: string; path: string }[]
      | undefined;
    const title = breadcrumbs?.[breadcrumbs.length - 1]?.name;
    tabsStore.openTab(path, title);
  },
  { immediate: true },
);

// ─── Sidebar nav items ─────────────────────────────────────────────────────
function renderIcon(iconName?: string) {
  if (!iconName) return undefined;
  // @ts-expect-error Dynamic icon loading based on string name
  const Comp = Icons[iconName] || LabIcons[iconName];
  return Comp ? h(Comp) : undefined;
}

const navItems = computed(() => {
  if (!userStore.userInfo?.roles) return [];
  const allMenus = userStore.userInfo.roles.flatMap((r) => r.menus || []);

  // Deduplicate by ID
  const uniqueMenus = Array.from(
    new Map(allMenus.map((m) => [m.id, m])).values(),
  );

  // Filter out BUTTON types and non-visible menus
  const navMenus = uniqueMenus.filter(
    (m) => m.type !== "BUTTON" && m.is_visible,
  );

  // Sort by sort_order
  navMenus.sort((a, b) => a.sort_order - b.sort_order);

  // Build tree
  const menuMap = new Map();
  navMenus.forEach((m) => menuMap.set(m.id, { ...m, children: [] }));

  const tree: Record<string, unknown>[] = [];
  navMenus.forEach((m) => {
    if (m.parent_id && menuMap.has(m.parent_id)) {
      menuMap.get(m.parent_id).children.push(menuMap.get(m.id));
    } else {
      tree.push(menuMap.get(m.id));
    }
  });

  if (
    tree.length === 0 &&
    (userStore.roles.includes("superadmin") ||
      userStore.roles.includes("admin") ||
      userStore.userInfo?.username === "admin")
  ) {
    return [
      {
        itemKey: "platform-group",
        text: "平台基础管理(系统默认)",
        icon: renderIcon("IconServer"),
        items: [
          {
            itemKey: "/admin/organizations",
            text: "组织架构管理",
            icon: renderIcon("IconTree"),
          },
          {
            itemKey: "/admin/tenants",
            text: "租户管理",
            icon: renderIcon("IconHome"),
          },
          {
            itemKey: "/admin/users",
            text: "用户管理",
            icon: renderIcon("IconUserGroup"),
          },
          {
            itemKey: "/admin/roles",
            text: "角色与权限配置",
            icon: renderIcon("IconShield"),
          },
          {
            itemKey: "/admin/menus",
            text: "菜单与权限管理",
            icon: renderIcon("IconList"),
          },
        ],
      },
      {
        itemKey: "security-group",
        text: "安全与集成",
        icon: renderIcon("IconSetting"),
        items: [
          {
            itemKey: "/admin/sso",
            text: "SSO集成设置",
            icon: renderIcon("IconKey"),
          },
          {
            itemKey: "/admin/audit",
            text: "审计日志",
            icon: renderIcon("IconList"),
          },
        ],
      },
    ];
  }

  // Map to Semi UI Nav format
  function mapToNavItems(
    menus: Record<string, unknown>[],
  ): Record<string, unknown>[] {
    return menus.map((m) => {
      const item: Record<string, unknown> = {
        itemKey: m.path || m.id,
        text: m.name,
        icon: renderIcon(m.icon as string | undefined),
      };
      if (Array.isArray(m.children) && m.children.length > 0) {
        item.items = mapToNavItems(m.children as Record<string, unknown>[]);
      }
      return item;
    });
  }

  return mapToNavItems(tree);
});

const currentRoutePath = computed(() => route.path);

const onSelect = (data: { itemKey?: string | number }) => {
  if (data.itemKey && String(data.itemKey).startsWith("/")) {
    router.push(String(data.itemKey));
  }
};

const isCollapsed = ref(false);
const onCollapseChange = (collapse: boolean) => {
  isCollapsed.value = collapse;
};
</script>

<style scoped>
.custom-scrollbar::-webkit-scrollbar {
  width: 6px;
  height: 6px;
}
.custom-scrollbar::-webkit-scrollbar-track {
  background: transparent;
}
.custom-scrollbar::-webkit-scrollbar-thumb {
  background-color: var(--semi-color-fill-1);
  border-radius: 20px;
}
.custom-scrollbar:hover::-webkit-scrollbar-thumb {
  background-color: var(--semi-color-fill-2);
}
</style>
