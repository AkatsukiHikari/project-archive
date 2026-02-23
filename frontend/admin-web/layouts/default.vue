<template>
  <div class="flex h-screen w-full bg-base-200 text-base-content">
    <!-- Sidebar -->
    <aside class="w-64 bg-base-100 shadow-lg hidden md:flex flex-col z-20">
      <div
        class="h-16 flex items-center justify-center border-b border-base-300"
      >
        <h1 class="text-xl font-bold text-primary">SAMS Archive</h1>
      </div>

      <nav class="flex-1 overflow-y-auto py-4">
        <ul class="menu menu-md w-full px-2 gap-1">
          <li>
            <NuxtLink to="/" active-class="active">
              <Icon name="heroicons:home" class="w-5 h-5" />
              Dashboard
            </NuxtLink>
          </li>

          <!-- Dynamic Menu Loop -->
          <li v-for="route in menuRoutes" :key="route.path">
            <NuxtLink
              v-if="!route.children"
              :to="route.path"
              active-class="active"
            >
              <Icon
                :name="route.meta?.icon || 'heroicons:document'"
                class="w-5 h-5"
              />
              {{ route.meta?.title || route.name }}
            </NuxtLink>

            <details v-else open>
              <summary>
                <Icon
                  :name="route.meta?.icon || 'heroicons:folder'"
                  class="w-5 h-5"
                />
                {{ route.meta?.title || route.name }}
              </summary>
              <ul>
                <li v-for="child in route.children" :key="child.path">
                  <NuxtLink :to="child.path" active-class="active">
                    {{ child.meta?.title || child.name }}
                  </NuxtLink>
                </li>
              </ul>
            </details>
          </li>
        </ul>
      </nav>

      <div
        class="p-4 border-t border-base-300 text-xs text-center text-base-content/50"
      >
        &copy; 2026 SAMS v2.0
      </div>
    </aside>

    <!-- Main Content Area -->
    <div class="flex-1 flex flex-col h-screen overflow-hidden relative">
      <!-- Header (AppHeader component) -->
      <AppHeader />

      <!-- Content Scroll Area -->
      <main class="flex-1 overflow-y-auto bg-base-200 p-6">
        <slot />
      </main>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useUserStore } from "@/stores/user";
import { usePermissionStore } from "@/stores/permission";
import AppHeader from "@/components/layout/AppHeader.vue";

const userStore = useUserStore();
const permissionStore = usePermissionStore();

// Computed for menu items
const menuRoutes = computed(() => permissionStore.menuRoutes);

// Initialize menu
onMounted(() => {
  if (userStore.roles && userStore.roles.length > 0) {
    const routes = useRouter()
      .getRoutes()
      .filter((r) => !r.path.includes(":") && !r.meta.hidden);
    permissionStore.generateRoutes(userStore.roles, routes);
  }
});
</script>

<style scoped>
.router-link-active {
  @apply bg-primary/10 text-primary font-medium;
}
</style>
