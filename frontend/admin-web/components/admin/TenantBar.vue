<template>
  <div
    class="flex items-center gap-3 px-4 py-2.5 rounded-xl mb-5"
    style="background: var(--semi-color-fill-0); border: 1px solid var(--semi-color-border)"
  >
    <Icon name="heroicons:building-office" class="w-4 h-4 shrink-0" style="color: var(--semi-color-text-2)" />
    <span class="text-[13px] shrink-0" style="color: var(--semi-color-text-1)">管理租户</span>
    <NSelect
      v-model:value="adminStore.currentTenantId"
      :loading="adminStore.loading"
      :options="tenantOptions"
      size="small"
      placeholder="请选择租户"
      style="width: 220px"
      @update:value="(v: string) => { adminStore.setCurrentTenant(v); emit('change', v) }"
    />
    <slot />
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted } from "vue";
import { NSelect } from "naive-ui";
import { useAdminStore } from "@/stores/admin";

const adminStore = useAdminStore();
const emit = defineEmits<{ change: [tenantId: string] }>();

const tenantOptions = computed(() =>
  adminStore.tenants.map((t) => ({
    label: `${t.name} (${t.code})`,
    value: t.id,
  })),
);

onMounted(() => {
  adminStore.fetchTenants();
});
</script>
