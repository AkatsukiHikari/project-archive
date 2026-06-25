<template>
  <div class="flex gap-3 overflow-hidden -my-6" style="height: calc(100vh - 176px)">

    <!-- ════════════════════════════════════════════════════════
         侧边栏（历史会话）
    ════════════════════════════════════════════════════════ -->
    <div
      class="flex flex-col flex-shrink-0 rounded-xl overflow-hidden transition-all duration-200"
      :style="{ width: sidebarCollapsed ? '52px' : '220px' }"
      style="background:var(--semi-color-bg-0);border:1px solid var(--semi-color-border)"
    >
      <div
        class="flex items-center gap-1.5 p-2.5 flex-shrink-0 min-h-[52px]"
        :class="sidebarCollapsed ? 'flex-col justify-center' : ''"
        style="border-bottom:1px solid var(--semi-color-border)"
      >
        <template v-if="!sidebarCollapsed">
          <button
            class="flex-1 min-w-0 flex items-center gap-2 px-2.5 py-1.5 rounded-lg border bg-transparent text-[13px] font-medium cursor-pointer whitespace-nowrap transition-colors"
            style="border-color:var(--semi-color-border);color:var(--semi-color-text-1)"
            @click="startNewChat"
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

      <div
        class="flex-1 overflow-y-auto overflow-x-hidden px-1.5 py-2 flex flex-col gap-px transition-opacity duration-150"
        :class="sidebarCollapsed ? 'opacity-0 pointer-events-none' : 'opacity-100'"
      >
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
          <div
            class="w-8 h-8 rounded-xl flex items-center justify-center"
            style="background:linear-gradient(135deg, oklch(var(--p)) 0%, oklch(var(--p)/0.72) 100%); box-shadow:0 2px 10px oklch(var(--p)/0.35)"
          >
            <Icon name="heroicons:sparkles" class="w-4 h-4 text-white" />
          </div>
          <h1 class="text-[15px] font-semibold leading-tight" style="color:var(--semi-color-text-0)">AI 档案助手</h1>
        </div>

        <div class="flex items-center gap-2">
          <NPopover trigger="hover" placement="bottom-end" :style="{ maxWidth: '280px' }">
            <template #trigger>
              <div
                class="relative flex items-center gap-1 px-2.5 py-1 rounded-full text-[11.5px] font-medium cursor-pointer transition-all"
                :style="{
                  background: tierMeta.bg,
                  color: tierMeta.fg,
                  boxShadow: `0 0 0 1px ${tierMeta.border} inset, 0 0 8px ${tierMeta.glow}`,
                }"
                @click="cycleModelTier"
              >
                <Icon :name="tierMeta.icon" class="w-3 h-3" />
                {{ activeModelTier }}
              </div>
            </template>
            <div class="text-[12px] flex flex-col gap-2">
              <div class="font-semibold text-[13px]" style="color:var(--semi-color-text-0)">模型档位</div>
              <div class="flex flex-col gap-1.5">
                <div v-for="t in TIER_INFO" :key="t.tier" class="flex items-start gap-2">
                  <span
                    class="text-[10.5px] px-1.5 py-0.5 rounded font-medium tabular-nums shrink-0 mt-0.5"
                    :style="{ background: t.bg, color: t.fg }"
                  >{{ t.tier }}</span>
                  <div class="leading-snug" style="color:var(--semi-color-text-1)">
                    <span class="font-medium" style="color:var(--semi-color-text-0)">{{ t.summary }}</span>
                    · {{ t.use }}
                  </div>
                </div>
              </div>
              <div class="text-[11px] pt-1 mt-0.5" style="border-top:1px solid var(--semi-color-border);color:var(--semi-color-text-3)">
                点击徽章循环切换 · 当前会话后续消息生效
              </div>
            </div>
          </NPopover>
          <NButton text size="small" @click="router.push('/ai/knowledge')">
            <template #icon><Icon name="heroicons:book-open" class="w-3.5 h-3.5" /></template>
            知识库
          </NButton>
        </div>
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
          scenario-code="qa"
          :model-tier="activeModelTier"
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
import { NButton, NPopover } from "naive-ui";
import type { ChatMessage } from "@/components/dashboard";
import type { ModelTier } from "@/api/ai";

definePageMeta({
  layout: "archive",
  middleware: "auth",
  breadcrumb: [{ name: "AI 档案助手", path: "/ai" }],
});
useHead({ title: "AI 档案助手" });

const router = useRouter();
const route = useRoute();

// ── 历史会话（本地持久化）────────────────────────────────────────────────────
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
  } catch {
    return [];
  }
};

const saveToStorage = (list: ConvRecord[]) => {
  localStorage.setItem(STORAGE_KEY, JSON.stringify(list));
};

// ── 模型档位 ──────────────────────────────────────────────────────────────────
const activeModelTier = ref<ModelTier>("准");

const tierMeta = computed(() => {
  switch (activeModelTier.value) {
    case "快":
      return { bg: "oklch(0.94 0.04 200)", fg: "oklch(0.45 0.12 200)", border: "oklch(0.6 0.15 200/0.4)", glow: "oklch(0.7 0.18 200/0.25)", icon: "heroicons:bolt" };
    case "思考":
      return { bg: "oklch(0.94 0.05 290)", fg: "oklch(0.4 0.18 290)", border: "oklch(0.55 0.2 290/0.4)", glow: "oklch(0.65 0.22 290/0.25)", icon: "heroicons:cpu-chip" };
    default:
      return { bg: "oklch(var(--p)/0.12)", fg: "oklch(var(--p))", border: "oklch(var(--p)/0.35)", glow: "oklch(var(--p)/0.2)", icon: "heroicons:sparkles" };
  }
});

const TIER_INFO = [
  { tier: "快", summary: "毫秒级响应", use: "简单问答 / 检索改写 / 轻量摘要", bg: "oklch(0.94 0.04 200)", fg: "oklch(0.4 0.14 200)" },
  { tier: "准", summary: "默认档位", use: "编目抽取 / 复杂综述 / 业务建议", bg: "oklch(var(--p)/0.12)", fg: "oklch(var(--p))" },
  { tier: "思考", summary: "深度推理", use: "跨档案关联 / 拟稿 / 复杂分析", bg: "oklch(0.94 0.05 290)", fg: "oklch(0.4 0.18 290)" },
];

const TIER_ORDER: ModelTier[] = ["快", "准", "思考"];
const cycleModelTier = () => {
  const idx = TIER_ORDER.indexOf(activeModelTier.value);
  activeModelTier.value = TIER_ORDER[(idx + 1) % TIER_ORDER.length] ?? "准";
};

// ── 会话状态 ──────────────────────────────────────────────────────────────────
const sidebarCollapsed = ref(false);
const conversations = ref<ConvRecord[]>([]);
const activeConvId = ref("");
const activeMessages = ref<ChatMessage[]>([]);
const activeConversationId = ref("");
const chatKey = ref(0);
const initialQuery = ref("");

onMounted(() => {
  conversations.value = loadFromStorage();
  if (route.query.q) initialQuery.value = String(route.query.q);
});

const startNewChat = () => {
  activeConvId.value = "";
  activeMessages.value = [];
  activeConversationId.value = "";
  initialQuery.value = "";
  chatKey.value++;
};

const loadConversation = (conv: ConvRecord) => {
  if (conv.id === activeConvId.value) return;
  activeConvId.value = conv.id;
  activeMessages.value = [...conv.messages];
  activeConversationId.value = conv.conversationId;
  initialQuery.value = "";
  chatKey.value++;
};

const onMessagesUpdated = (messages: ChatMessage[], conversationId: string) => {
  if (messages.length === 0) return;

  const firstUser = messages.find((m) => m.role === "user");
  const title = firstUser
    ? firstUser.content.slice(0, 28) + (firstUser.content.length > 28 ? "…" : "")
    : "新对话";

  const resolvedId = activeConvId.value || `conv-${Date.now()}`;
  const list = [...conversations.value];
  const idx = list.findIndex((c) => c.id === resolvedId);

  const next: ConvRecord = {
    id: resolvedId,
    title,
    conversationId,
    messages: [...messages],
    updatedAt: Date.now(),
  };

  if (idx !== -1) list[idx] = next;
  else list.unshift(next);

  activeConvId.value = resolvedId;
  activeConversationId.value = conversationId;
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
  if (m < 1) return "刚刚";
  if (m < 60) return `${m} 分钟前`;
  const h = Math.floor(m / 60);
  if (h < 24) return `${h} 小时前`;
  const d = Math.floor(h / 24);
  if (d < 30) return `${d} 天前`;
  return new Date(ts).toLocaleDateString("zh-CN");
};
</script>
