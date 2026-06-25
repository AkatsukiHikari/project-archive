<template>
  <div class="flex flex-col gap-5">
    <div class="flex items-center gap-2.5">
      <div
        class="w-9 h-9 rounded-xl flex items-center justify-center"
        style="background: linear-gradient(135deg, oklch(var(--p)) 0%, oklch(var(--p)/0.72) 100%); box-shadow: 0 2px 10px oklch(var(--p)/0.35)"
      >
        <Icon name="heroicons:book-open" class="w-5 h-5 text-white" />
      </div>
      <h1 class="text-base font-semibold" style="color: var(--semi-color-text-0)">AI 知识库</h1>
    </div>

    <!-- 状态卡 -->
    <div class="pro-card p-5 flex flex-col gap-4">
      <div class="flex items-center justify-between">
        <span class="text-sm font-medium" style="color: var(--semi-color-text-1)">知识库状态</span>
        <NButton text size="small" :loading="loadingStatus" @click="loadStatus">
          <template #icon><Icon name="heroicons:arrow-path" class="w-4 h-4" /></template>
          刷新
        </NButton>
      </div>

      <div v-if="status" class="flex flex-col gap-3">
        <div class="flex items-center gap-6">
          <div class="flex flex-col">
            <span class="text-2xl font-semibold tabular-nums" style="color: var(--semi-color-text-0)">{{ status.doc_count ?? "—" }}</span>
            <span class="text-xs" style="color: var(--semi-color-text-3)">已入库文档</span>
          </div>
          <NTag :type="status.enabled ? 'success' : 'warning'" round size="small">
            {{ status.enabled ? "知识库已配置" : "未配置知识库 API" }}
          </NTag>
          <NTag v-if="status.error" type="error" round size="small">{{ status.error }}</NTag>
        </div>
        <div v-if="status.name" class="text-xs flex items-center gap-2 px-3 py-2 rounded-lg" style="background: var(--semi-color-fill-0); color: var(--semi-color-text-2)">
          <Icon name="heroicons:circle-stack" class="w-4 h-4" />
          <strong style="color: var(--semi-color-text-0)">{{ status.name }}</strong>
        </div>
      </div>
      <NSpin v-else-if="loadingStatus" size="small" />
    </div>

    <!-- 同步 -->
    <div class="pro-card p-5 flex flex-col gap-3">
      <span class="text-sm font-medium" style="color: var(--semi-color-text-1)">全量同步</span>
      <div class="flex items-center gap-3">
        <NButton type="primary" :loading="syncing" @click="doSync">
          <template #icon><Icon name="heroicons:cloud-arrow-up" class="w-4 h-4" /></template>
          一键全量同步
        </NButton>
        <span v-if="lastSynced !== null" class="text-sm" style="color: var(--semi-color-text-2)">本次同步 {{ lastSynced }} 条</span>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { onMounted, ref } from "vue";
import { NButton, NSpin, NTag, useMessage } from "naive-ui";
import { AiAdminAPI, type KBStatus } from "@/api/ai";

definePageMeta({
  layout: "archive",
  middleware: "auth",
  breadcrumb: [
    { name: "AI 档案助手", path: "/ai" },
    { name: "知识库管理", path: "/ai/knowledge" },
  ],
});
useHead({ title: "AI 知识库" });

const message = useMessage();
const status = ref<KBStatus | null>(null);
const loadingStatus = ref(false);
const syncing = ref(false);
const lastSynced = ref<number | null>(null);

async function loadStatus() {
  loadingStatus.value = true;
  try {
    const res = await AiAdminAPI.kbStatus();
    status.value = res.data;
  } finally {
    loadingStatus.value = false;
  }
}

async function doSync() {
  syncing.value = true;
  try {
    const res = await AiAdminAPI.kbRebuild();
    if (res.code === 0) {
      lastSynced.value = res.data.synced;
      message.success(`已同步 ${res.data.synced} 条档案到知识库`);
      loadStatus();
    } else {
      message.error(res.message);
    }
  } catch {
    message.error("同步失败");
  } finally {
    syncing.value = false;
  }
}

onMounted(loadStatus);
</script>
