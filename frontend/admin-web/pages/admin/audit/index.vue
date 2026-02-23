<template>
  <div class="flex flex-col gap-4">
    <!-- 顶部租户选择 -->
    <div
      class="bg-[var(--semi-color-bg-0)] rounded-xl border border-[var(--semi-color-border)] shadow-sm p-4 flex items-center justify-between"
    >
      <div class="flex items-center gap-4">
        <span class="font-medium text-[var(--semi-color-text-0)] text-sm"
          >当前管理租户：</span
        >
        <Select
          v-model="currentTenantId"
          @change="handleTenantChange"
          :style="{ width: '280px' }"
          :loading="tenantsLoading"
          placeholder="请选择租户"
        >
          <Select.Option v-for="t in tenants" :key="t.id" :value="t.id">
            {{ t.name }} ({{ t.code }})
          </Select.Option>
        </Select>
      </div>
      <div class="flex gap-2">
        <Button theme="light" icon="material-symbols:download" disabled
          >导出报表</Button
        >
      </div>
    </div>

    <div
      class="bg-[var(--semi-color-bg-0)] rounded-xl border border-[var(--semi-color-border)] shadow-sm p-6 min-h-[500px]"
    >
      <div class="flex justify-between items-center mb-6">
        <h2 class="text-lg font-semibold text-[var(--semi-color-text-0)]">
          系统安全审计
        </h2>
      </div>
      <Table
        :columns="columns"
        :data-source="auditLogs"
        :loading="loading"
        empty-text="暂无审计日志"
        rowKey="id"
      />
    </div>
  </div>
</template>

<script setup lang="tsx">
import { ref, onMounted } from "vue";
import { definePageMeta } from "#imports";
import {
  Button,
  Table,
  Select,
  Toast,
  Tag,
  Popover,
} from "@kousum/semi-ui-vue";
import { TenantAPI, type Tenant } from "@/api/iam";
import { AuditAPI, type AuditLog } from "@/api/audit";

definePageMeta({ layout: "admin" });

const tenants = ref<Tenant[]>([]);
const currentTenantId = ref<string>("");
const tenantsLoading = ref(false);

const auditLogs = ref<AuditLog[]>([]);
const loading = ref(false);

const columns = [
  {
    title: "操作时间",
    dataIndex: "create_time",
    render: (text: string) => new Date(text).toLocaleString(),
  },
  { title: "操作员 ID", dataIndex: "user_id" },
  {
    title: "操作模块",
    dataIndex: "module",
    render: (text: string) => <Tag>{text}</Tag>,
  },
  {
    title: "动作",
    dataIndex: "action",
    render: (text: string) => <span class="font-medium">{text}</span>,
  },
  { title: "IP 地址", dataIndex: "ip_address" },
  {
    title: "状态",
    dataIndex: "status",
    render: (val: string) => (
      <Tag color={val === "success" ? "green" : ("red" as any)}>
        {val === "success" ? "成功" : "失败"}
      </Tag>
    ),
  },
  {
    title: "详情",
    dataIndex: "details",
    render: (_text: any, record: AuditLog) => {
      if (!record.details) return <span>-</span>;
      // 简单展示 JSON 格式详情
      return (
        <Popover
          content={
            <div class="p-2 max-w-xs break-all">
              <pre class="text-xs">
                {JSON.stringify(record.details, null, 2)}
              </pre>
            </div>
          }
          position="topLeft"
        >
          <span class="text-[var(--semi-color-primary)] cursor-pointer hover:underline text-xs">
            查看详细
          </span>
        </Popover>
      );
    },
  },
];

onMounted(async () => {
  await fetchTenants();
});

async function fetchTenants() {
  tenantsLoading.value = true;
  try {
    const res = await TenantAPI.list();
    tenants.value = res.data.data || [];
    if (tenants.value.length > 0) {
      currentTenantId.value = tenants.value[0].id;
      handleTenantChange(currentTenantId.value);
    }
  } catch (err: any) {
    Toast.error(err.message || "加载租户失败");
  } finally {
    tenantsLoading.value = false;
  }
}

function handleTenantChange(val: any) {
  currentTenantId.value = val as string;
  fetchAuditLogs();
}

async function fetchAuditLogs() {
  if (!currentTenantId.value) return;
  loading.value = true;
  try {
    const res = await AuditAPI.list({
      tenant_id: currentTenantId.value,
      limit: 100,
    });
    // Assuming backend returns an array structure directly inside `res.data` or `res.data.data`
    auditLogs.value = res.data.data || res.data || [];
  } catch (err: any) {
    Toast.error(err.message || "加载审计日志失败");
  } finally {
    loading.value = false;
  }
}
</script>
