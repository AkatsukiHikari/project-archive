<template>
  <div class="flex flex-col gap-4">
    <div class="rounded-xl border p-4 flex items-center justify-between"
      style="background:var(--semi-color-bg-0);border-color:var(--semi-color-border)">
      <div class="flex items-center gap-4">
        <span class="font-medium text-sm" style="color:var(--semi-color-text-0)">当前管理租户：</span>
        <NSelect
          v-model:value="currentTenantId"
          :options="tenantOptions"
          :loading="tenantsLoading"
          style="width:280px"
          placeholder="请选择租户"
          @update:value="handleTenantChange"
        />
      </div>
      <NButton disabled>
        <template #icon><Icon name="heroicons:arrow-down-tray" class="w-4 h-4" /></template>
        导出报表
      </NButton>
    </div>

    <div class="rounded-xl border p-6 min-h-[500px]"
      style="background:var(--semi-color-bg-0);border-color:var(--semi-color-border)">
      <h2 class="text-lg font-semibold mb-6" style="color:var(--semi-color-text-0)">系统安全审计</h2>
      <NDataTable
        :columns="columns"
        :data="auditLogs"
        :loading="loading"
        :pagination="{ pageSize: 20, showSizePicker: true, pageSizes: [20, 50, 100] }"
        :row-key="(row: AuditLog) => row.id"
      >
        <template #empty><NEmpty description="暂无审计日志" class="py-10" /></template>
      </NDataTable>
    </div>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted } from "vue";
import { NButton, NSelect, NDataTable, NEmpty, NTag, NPopover, useMessage } from "naive-ui";
import { TenantAPI, type Tenant } from "@/api/iam";
import { AuditAPI, type AuditLog } from "@/api/audit";

definePageMeta({ layout: "admin", middleware: "auth" });

const message = useMessage();
const tenants = ref<Tenant[]>([]);
const currentTenantId = ref<string | null>(null);
const tenantsLoading = ref(false);
const auditLogs = ref<AuditLog[]>([]);
const loading = ref(false);

const tenantOptions = computed(() => tenants.value.map((t) => ({ label: `${t.name} (${t.code})`, value: t.id })));

const columns = [
  {
    title: "操作时间", key: "create_time",
    render: (row: AuditLog) => new Date(row.create_time).toLocaleString("zh-CN"),
  },
  { title: "操作员 ID", key: "user_id" },
  {
    title: "操作模块", key: "module",
    render: (row: AuditLog) => <NTag size="small">{row.module}</NTag>,
  },
  {
    title: "动作", key: "action",
    render: (row: AuditLog) => <span class="font-medium">{row.action}</span>,
  },
  { title: "IP 地址", key: "ip_address" },
  {
    title: "状态", key: "status",
    render: (row: AuditLog) => (
      <NTag type={row.status === "success" ? "success" : "error"} size="small">
        {row.status === "success" ? "成功" : "失败"}
      </NTag>
    ),
  },
  {
    title: "详情", key: "details",
    render: (row: AuditLog) => {
      if (!row.details) return <span>-</span>;
      return (
        <NPopover trigger="hover">
          {{
            trigger: () => (
              <span class="cursor-pointer hover:underline text-xs" style="color:var(--semi-color-primary)">
                查看详细
              </span>
            ),
            default: () => (
              <div class="p-2 max-w-xs break-all">
                <pre class="text-xs">{JSON.stringify(row.details, null, 2)}</pre>
              </div>
            ),
          }}
        </NPopover>
      );
    },
  },
];

onMounted(fetchTenants);

async function fetchTenants() {
  tenantsLoading.value = true;
  try {
    const res = (await TenantAPI.list()) as any;
    tenants.value = res.data || [];
    const firstTenant = tenants.value[0];
    if (firstTenant) {
      currentTenantId.value = firstTenant.id;
      fetchAuditLogs();
    }
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "加载租户失败");
  } finally {
    tenantsLoading.value = false;
  }
}

function handleTenantChange(val: string) {
  currentTenantId.value = val;
  fetchAuditLogs();
}

async function fetchAuditLogs() {
  if (!currentTenantId.value) return;
  loading.value = true;
  try {
    const res = (await AuditAPI.list({ tenant_id: currentTenantId.value, limit: 100 })) as any;
    auditLogs.value = res.data || [];
  } catch (err: unknown) {
    message.error(err instanceof Error ? err.message : "加载审计日志失败");
  } finally {
    loading.value = false;
  }
}
</script>
