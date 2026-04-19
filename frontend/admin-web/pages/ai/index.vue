<template>
  <div class="flex h-full gap-3 min-h-0">

    <!-- ════════════════════════════════════════════════════════
         侧边栏
    ════════════════════════════════════════════════════════ -->
    <div
      class="flex flex-col flex-shrink-0 rounded-xl overflow-hidden transition-all duration-200"
      :style="{ width: sidebarCollapsed ? '52px' : '220px' }"
      style="background:var(--semi-color-bg-0);border:1px solid var(--semi-color-border)"
    >
      <!-- 头部 -->
      <div
        class="flex items-center gap-1.5 p-2.5 flex-shrink-0 min-h-[52px]"
        :class="sidebarCollapsed ? 'flex-col justify-center' : ''"
        style="border-bottom:1px solid var(--semi-color-border)"
      >
        <!-- 展开态 -->
        <template v-if="!sidebarCollapsed">
          <button
            class="flex-1 min-w-0 flex items-center gap-2 px-2.5 py-1.5 rounded-lg border bg-transparent text-[13px] font-medium cursor-pointer whitespace-nowrap transition-colors"
            style="border-color:var(--semi-color-border);color:var(--semi-color-text-1)"
            @click="startNewChat"
            @mouseenter="(e) => Object.assign((e.currentTarget as HTMLElement).style, { borderColor: 'oklch(var(--p))', color: 'oklch(var(--p))', background: 'oklch(var(--p)/0.06)' })"
            @mouseleave="(e) => Object.assign((e.currentTarget as HTMLElement).style, { borderColor: 'var(--semi-color-border)', color: 'var(--semi-color-text-1)', background: 'transparent' })"
          >
            <Icon name="heroicons:pencil-square" class="w-4 h-4 shrink-0" />
            <span>新对话</span>
          </button>
          <button
            class="w-8 h-8 flex items-center justify-center rounded-lg border-none bg-transparent cursor-pointer flex-shrink-0 transition-colors hover:bg-[var(--semi-color-fill-0)]"
            style="color:var(--semi-color-text-2)"
            title="收起"
            @click="sidebarCollapsed = true"
          >
            <Icon name="heroicons:chevron-left" class="w-4 h-4" />
          </button>
        </template>

        <!-- 折叠态 -->
        <template v-else>
          <button
            class="w-8 h-8 flex items-center justify-center rounded-lg border-none bg-transparent cursor-pointer transition-colors hover:bg-[var(--semi-color-fill-0)]"
            style="color:var(--semi-color-text-1)"
            title="新对话"
            @click="startNewChat"
          >
            <Icon name="heroicons:pencil-square" class="w-4 h-4" />
          </button>
          <button
            class="w-8 h-8 flex items-center justify-center rounded-lg border-none bg-transparent cursor-pointer transition-colors hover:bg-[var(--semi-color-fill-0)]"
            style="color:var(--semi-color-text-2)"
            title="展开"
            @click="sidebarCollapsed = false"
          >
            <Icon name="heroicons:chevron-right" class="w-4 h-4" />
          </button>
        </template>
      </div>

      <!-- 历史列表 -->
      <div
        class="flex-1 overflow-y-auto overflow-x-hidden px-1.5 py-2 flex flex-col gap-px transition-opacity duration-150"
        :class="sidebarCollapsed ? 'opacity-0 pointer-events-none' : 'opacity-100'"
      >
        <!-- 空态 -->
        <div v-if="conversations.length === 0" class="flex flex-col items-center justify-center py-8 gap-2" style="color:var(--semi-color-text-3)">
          <Icon name="heroicons:chat-bubble-left-ellipsis" class="w-6 h-6 opacity-40" />
          <span class="text-xs">暂无历史对话</span>
        </div>

        <template v-else>
          <p class="text-[11px] font-semibold uppercase tracking-widest px-2 pb-1.5 pt-1" style="color:var(--semi-color-text-3)">
            历史对话
          </p>
          <button
            v-for="conv in conversations"
            :key="conv.id"
            class="group relative flex flex-col items-start gap-0.5 w-full px-2.5 py-2 pr-7 rounded-lg border-none bg-transparent cursor-pointer text-left transition-colors hover:bg-[var(--semi-color-fill-0)]"
            :style="conv.id === activeConvId ? 'background:oklch(var(--p)/0.1)' : ''"
            @click="loadConversation(conv)"
          >
            <span
              class="text-[12.5px] whitespace-nowrap overflow-hidden text-ellipsis max-w-full"
              :style="conv.id === activeConvId ? 'color:oklch(var(--p));font-weight:600' : 'color:var(--semi-color-text-0)'"
            >{{ conv.title }}</span>
            <span class="text-[11px]" style="color:var(--semi-color-text-3)">{{ relativeTime(conv.updatedAt) }}</span>
            <!-- 删除按钮（hover 时才显示） -->
            <span
              class="absolute top-1/2 right-1.5 -translate-y-1/2 w-[18px] h-[18px] flex items-center justify-center rounded cursor-pointer opacity-0 group-hover:opacity-100 transition-all hover:bg-[oklch(var(--er)/0.12)]"
              style="color:var(--semi-color-text-3)"
              role="button"
              title="删除"
              @click.stop="deleteConversation(conv.id)"
            >
              <Icon name="heroicons:x-mark" class="w-3 h-3" />
            </span>
          </button>
        </template>
      </div>
    </div>

    <!-- ════════════════════════════════════════════════════════
         主内容区
    ════════════════════════════════════════════════════════ -->
    <div class="flex-1 min-w-0 flex flex-col gap-2.5">

      <!-- 标题栏 -->
      <div class="flex items-center justify-between flex-shrink-0">
        <div class="flex items-center gap-2.5">
          <div class="w-8 h-8 rounded-xl flex items-center justify-center" style="background:oklch(var(--p)/0.12)">
            <Icon name="heroicons:sparkles" class="w-4 h-4" style="color:oklch(var(--p))" />
          </div>
          <div>
            <h1 class="text-[15px] font-semibold leading-tight" style="color:var(--semi-color-text-0)">AI 档案助手</h1>
            <p class="text-[11px] leading-tight" style="color:var(--semi-color-text-3)">
              {{ activeConvId ? conversationLabel : '开始新对话' }}
            </p>
          </div>
        </div>
        <NButton text size="small" @click="router.push('/ai/knowledge')">
          <template #icon><Icon name="heroicons:book-open" class="w-3.5 h-3.5" /></template>
          知识库
        </NButton>
      </div>

      <!-- 聊天面板 -->
      <div
        class="flex-1 min-h-0 rounded-xl overflow-hidden"
        style="border:1px solid var(--semi-color-border);background:var(--semi-color-bg-0)"
      >
        <DashboardRagChatPanel
          :key="chatKey"
          :initial-query="initialQuery"
          :initial-messages="activeMessages"
          :initial-conversation-id="activeConversationId"
          class="h-full"
          @messages-updated="onMessagesUpdated"
        />
      </div>

      <p class="flex-shrink-0 text-center text-[11px]" style="color:var(--semi-color-text-3)">
        AI 回答仅供参考，请以正式档案为准
      </p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { useRouter, useRoute } from "vue-router";
import { NButton } from "naive-ui";
import type { ChatMessage } from "@/components/dashboard/RagChatPanel.vue";

definePageMeta({
  layout: "portal",
  middleware: "auth",
  breadcrumb: [{ name: "AI 档案助手", path: "/ai" }],
});

const router = useRouter();
const route  = useRoute();

// ── 持久化结构 ──────────────────────────────────────────────────────────────
interface ConvRecord {
  id: string;
  title: string;
  conversationId: string;
  messages: ChatMessage[];
  updatedAt: number;
}

const STORAGE_KEY = "sams_ai_conversations";

const loadFromStorage = (): ConvRecord[] => {
  try {
    const raw = localStorage.getItem(STORAGE_KEY);
    return raw
      ? (JSON.parse(raw) as ConvRecord[]).sort((a, b) => b.updatedAt - a.updatedAt)
      : [];
  } catch { return []; }
};

const saveToStorage = (list: ConvRecord[]) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
};

// ── 状态 ────────────────────────────────────────────────────────────────────
const sidebarCollapsed    = ref(false);
const conversations       = ref<ConvRecord[]>([]);
const activeConvId        = ref("");
const activeMessages      = ref<ChatMessage[]>([]);
const activeConversationId = ref("");
const chatKey             = ref(0);
const initialQuery        = ref("");

const conversationLabel = computed(() =>
  conversations.value.find((c) => c.id === activeConvId.value)?.title ?? "",
);

onMounted(() => {
  conversations.value = loadFromStorage();
  if (route.query.q) initialQuery.value = String(route.query.q);
});

// ── 操作 ────────────────────────────────────────────────────────────────────
const startNewChat = () => {
  activeConvId.value         = "";
  activeMessages.value       = [];
  activeConversationId.value = "";
  initialQuery.value         = "";
  chatKey.value++;
};

const loadConversation = (conv: ConvRecord) => {
  if (conv.id === activeConvId.value) return;
  activeConvId.value         = conv.id;
  activeMessages.value       = [...conv.messages];
  activeConversationId.value = conv.conversationId;
  initialQuery.value         = "";
  chatKey.value++;
};

const onMessagesUpdated = (messages: ChatMessage[], conversationId: string) => {
  if (messages.length === 0) return;

  const firstUser = messages.find((m) => m.role === "user");
  const title = firstUser
    ? firstUser.content.slice(0, 28) + (firstUser.content.length > 28 ? "…" : "")
    : "新对话";

  const list = [...conversations.value];

  if (activeConvId.value) {
    const idx = list.findIndex((c) => c.id === activeConvId.value);
    if (idx !== -1) {
      const existing = list[idx];
      if (existing) list[idx] = { ...existing, title, conversationId, messages: [...messages], updatedAt: Date.now() };
    }
  } else {
    const newId = `conv-${Date.now()}`;
    activeConvId.value         = newId;
    activeConversationId.value = conversationId;
    list.unshift({ id: newId, title, conversationId, messages: [...messages], updatedAt: Date.now() });
  }

  conversations.value = list.sort((a, b) => b.updatedAt - a.updatedAt);
  saveToStorage(conversations.value);
};

const deleteConversation = (id: string) => {
  conversations.value = conversations.value.filter((c) => c.id !== id);
  saveToStorage(conversations.value);
  if (activeConvId.value === id) startNewChat();
};

const relativeTime = (ts: number): string => {
  const m = Math.floor((Date.now() - ts) / 60000);
  if (m < 1)  return "刚刚";
  if (m < 60) return `${m} 分钟前`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} 小时前`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d} 天前`;
  return new Date(ts).toLocaleDateString("zh-CN");
};
</script>
