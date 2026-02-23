<template>
  <Layout class="min-h-screen bg-[var(--semi-color-bg-0)]">
    <!-- Sidebar -->
    <LayoutSider
      class="bg-[var(--semi-color-bg-0)] border-r border-[var(--semi-color-border)] shadow-sm z-40"
      style="position: fixed; top: 0; left: 0; height: 100vh; width: 240px"
    >
      <Nav
        :default-open-keys="['platform-group', 'security-group']"
        :default-selected-keys="[currentRoutePath]"
        class="h-full overflow-y-auto w-full custom-scrollbar"
        :items="navItems"
        :header="{
          style: {
            padding: '16px 12px',
            display: 'flex',
            justifyContent: 'center',
          },
          logo: h(IconGallery, {
            style: { fontSize: '28px', marginTop: '4px' },
          }),
          text: h(
            'span',
            { class: 'font-bold text-lg leading-none ml-1' },
            '智慧档案平台',
          ),
        }"
        :footer="{ collapseButton: true }"
        @select="onSelect"
      />
    </LayoutSider>

    <Layout
      class="flex flex-col min-h-screen bg-[var(--semi-color-bg-1)]"
      style="margin-left: 240px; padding-top: 64px"
    >
      <!-- Subsystem Header Fixed Wrapper -->
      <div style="position: fixed; top: 0; right: 0; left: 240px; z-index: 30">
        <SystemHeader />
      </div>

      <LayoutContent class="p-6 flex-1 w-full">
        <slot />
      </LayoutContent>
      <!-- Footer -->
      <LayoutFooter class="shrink-0">
        <AppFooter />
      </LayoutFooter>
    </Layout>
  </Layout>
</template>

<script setup lang="ts">
import { useRouter, useRoute } from "vue-router";
import {
  Layout,
  LayoutSider,
  LayoutFooter,
  LayoutContent,
  Nav,
} from "@kousum/semi-ui-vue";
import {
  IconUserGroup,
  IconShield,
  IconKey,
  IconList,
  IconGallery,
  IconHome,
  IconSetting,
  IconServer,
} from "@kousum/semi-icons-vue";
import { IconTree } from "@kousum/semi-icons-lab-vue";
import SystemHeader from "@/components/layout/SystemHeader.vue";
import AppFooter from "@/components/layout/AppFooter.vue";

const router = useRouter();
const route = useRoute();

const navItems = [
  {
    itemKey: "platform-group",
    text: "平台基础管理",
    icon: h(IconServer),
    items: [
      {
        itemKey: "/admin/organizations",
        text: "组织架构管理",
        icon: h(IconTree),
      },
      { itemKey: "/admin/tenants", text: "租户管理", icon: h(IconHome) },
      { itemKey: "/admin/users", text: "用户管理", icon: h(IconUserGroup) },
      { itemKey: "/admin/roles", text: "角色与权限配置", icon: h(IconShield) },
    ],
  },
  {
    itemKey: "security-group",
    text: "安全与集成",
    icon: h(IconSetting),
    items: [
      { itemKey: "/admin/sso", text: "SSO集成设置", icon: h(IconKey) },
      { itemKey: "/admin/audit", text: "审计日志", icon: h(IconList) },
    ],
  },
];

const currentRoutePath = computed(() => route.path);

const onSelect = (data: { itemKey?: string | number }) => {
  if (data.itemKey) {
    router.push(String(data.itemKey));
  }
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
