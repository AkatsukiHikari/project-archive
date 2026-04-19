import { defineStore } from "pinia";
import { ref, computed } from "vue";
import { TenantAPI, type Tenant } from "@/api/iam";

export const useAdminStore = defineStore("admin", () => {
  const tenants = ref<Tenant[]>([]);
  const currentTenantId = ref<string>("");
  const loading = ref(false);

  const currentTenant = computed(
    () => tenants.value.find((t) => t.id === currentTenantId.value) ?? null,
  );

  async function fetchTenants() {
    if (loading.value || tenants.value.length > 0) return;
    loading.value = true;
    try {
      const res = await TenantAPI.list();
      tenants.value = (res as any).data || [];
      const firstTenant = tenants.value[0];
      if (firstTenant && !currentTenantId.value) {
        currentTenantId.value = firstTenant.id;
      }
    } catch {
      // silently fail — header already shows an error if tenant load fails
    } finally {
      loading.value = false;
    }
  }

  function setCurrentTenant(id: string) {
    currentTenantId.value = id;
  }

  return {
    tenants,
    currentTenantId,
    currentTenant,
    loading,
    fetchTenants,
    setCurrentTenant,
  };
});
