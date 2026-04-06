<template>
  <div class="flex flex-col h-full">

    <!-- 顶部栏 -->
    <div class="flex items-center justify-between mb-4 shrink-0">
      <div>
        <div class="flex items-center gap-2 mb-1">
          <div class="w-7 h-7 rounded-lg bg-primary/10 flex items-center justify-center">
            <Icon name="heroicons:sparkles" class="w-4 h-4 text-primary" />
          </div>
          <h1 class="text-[18px] font-bold" style="color: var(--semi-color-text-0);">
            AI 档案智能助手
          </h1>
          <Tag size="small" color="blue" shape="circle" style="font-size: 10px;">RAG</Tag>
        </div>
        <p class="text-[12px]" style="color: var(--semi-color-text-2);">
          基于 Dify + Ollama · 语义检索全库档案 · 支持多轮对话
        </p>
      </div>
      <div class="flex items-center gap-2">
        <Button theme="borderless" type="tertiary" size="small" @click="router.push('/ai/knowledge')">
          <template #icon><Icon name="heroicons:book-open" class="w-4 h-4" /></template>
          知识库管理
        </Button>
        <button
          class="new-chat-btn"
          @click="resetChat"
        >
          <Icon name="heroicons:plus" class="w-3.5 h-3.5" />
          新对话
        </button>
      </div>
    </div>

    <!-- 主对话区域 -->
    <Card
      :shadows="'always'"
      :header-line="false"
      :body-style="{ padding: 0, height: '100%', overflow: 'hidden' }"
      class="flex-1 min-h-0 overflow-hidden"
    >
      <DashboardRagChatPanel :key="chatKey" :initial-query="initialQuery" class="h-full" />
    </Card>

    <!-- 底部提示 -->
    <p class="text-center text-[11px] mt-3 shrink-0" style="color: var(--semi-color-text-2);">
      AI 回答仅供参考，请以正式档案为准 · 当前模型：{{ modelName }}
    </p>

  </div>
</template>

<script setup lang="ts">
import { ref, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { Card, Button, Tag } from "@kousum/semi-ui-vue";

definePageMeta({
  layout: "portal",
  middleware: "auth",
  breadcrumb: [{ name: "AI 档案助手", path: "/ai" }],
});

const router = useRouter();
const route = useRoute();

const chatKey = ref(0);
const initialQuery = ref("");
const modelName = ref("Ollama / qwen2.5");

onMounted(() => {
  // 从首页携带的快捷问题
  if (route.query.q) {
    initialQuery.value = String(route.query.q);
  }
});

function resetChat() {
  initialQuery.value = "";
  chatKey.value++;
}
</script>

<style scoped>
.new-chat-btn {
  display: inline-flex;
  align-items: center;
  gap: 5px;
  padding: 5px 14px;
  font-size: 13px;
  font-weight: 500;
  border-radius: 20px;
  border: 1px solid var(--semi-color-primary);
  color: var(--semi-color-primary);
  background: transparent;
  cursor: pointer;
  transition: background 0.15s, color 0.15s;
}
.new-chat-btn:hover {
  background: var(--semi-color-primary);
  color: #fff;
}
</style>
