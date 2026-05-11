<template>
  <div class="flex flex-col gap-4">
    <AdminPageHeader
      title="安全审计"
      description="查看系统操作日志，追踪用户行为与安全事件"
      icon="heroicons:shield-exclamation"
    />

    <ProTable
      :columns="columns"
      :data="auditLogs"
      :loading="loading"
      empty-content="暂无审计日志"
    >
      <template #toolbar-left>
        <NSelect
          v-model:value="currentTenantId"
          :options="tenantOptions"
          :loading="tenantsLoading"
          class="w-64"
          placeholder="选择租户"
          @update:value="handleTenantChange"
        />
      </template>
      <template #toolbar-right>
        <NButton disabled>
          <template #icon><Icon name="heroicons:arrow-down-tray" class="w-4 h-4" /></template>
          导出报表
        </NButton>
      </template>
    </ProTable>
  </div>
</template>

<script setup lang="tsx">
import { ref, computed, onMounted } from "vue";
import { NButton, NSelect, NTag, NPopover, useMessage } from "naive-ui";
import { TenantAPI, type Tenant } from "@/api/iam";
import { AuditAPI, type AuditLog } from "@/api/audit";
import { AdminPageHeader } from "@/components/admin";
import { ProTable } from "@/components/ui";

definePageMeta({ layout: "admin", middleware: "auth" });

const message = useMessage();
const tenants = ref<Tenant[]>([]);
const currentTenantId = ref<string | null>(null);
const tenantsLoading = ref(false);
const auditLogs = ref<AuditLog[]>([]);
const loading = ref(false);

const tenantOptions = computed(() =>
  tenants.value.map((t) => ({ label: `${t.name} (${t.code})`, value: t.id })),
);

const statusOptions = [
  { label: "成功", value: "success" },
  { label: "失败", value: "fail" },
];

const columns = [
  {
    title: "操作时间", key: "create_time",
    render: (row: AuditLog) => new Date(row.create_time).toLocaleString("zh-CN"),
  },
  { title: "操作员 ID", key: "user_id", search: { placeholder: "请输入操作员 ID" } },
  {
    title: "操作模块", key: "module",
    search: { placeholder: "请输入模块名" },
    render: (row: AuditLog) => <NTag size="small">{row.module}</NTag>,
  },
  {
    title: "动作", key: "action",
    search: { placeholder: "请输入动作" },
    render: (row: AuditLog) => <span class="font-medium">{row.action}</span>,
  },
  { title: "IP 地址", key: "ip_address", search: { placeholder: "请输入 IP" } },
  {
    title: "状态", key: "status",
    search: { type: "select" as const, options: statusOptions },
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
              <span class="cursor-pointer hover:underline text-xs text-primary">查看详细</span>
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
    const first = tenants.value[0];
    if (first) {
      currentTenantId.value = first.id;
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
