<template>
  <!-- CSS grid: 消息区自动占满剩余空间，输入区贴底不动 -->
  <div
    class="h-full overflow-hidden"
    style="display: grid; grid-template-rows: 1fr auto; background: var(--semi-color-bg-1); cursor: default;"
  >

    <!-- ── 消息列表（row 1，可滚动） ──────────────────── -->
    <div ref="scrollRef" class="overflow-y-auto min-h-0 px-5 py-5 space-y-5">

      <!-- 无消息欢迎态 -->
      <div
        v-if="messages.length === 0"
        class="flex flex-col items-center justify-center h-full text-center gap-5"
      >
        <div class="w-16 h-16 rounded-2xl bg-primary/10 flex items-center justify-center">
          <Icon name="heroicons:cpu-chip" class="w-9 h-9 text-primary" />
        </div>
        <div>
          <p class="text-[15px] font-semibold mb-1" style="color: var(--semi-color-text-0);">
            向档案库提问
          </p>
          <p class="text-[12px]" style="color: var(--semi-color-text-2);">
            可以询问档案内容、政策查阅、数据统计等
          </p>
        </div>
        <div class="flex flex-wrap gap-2 justify-center max-w-md">
          <button
            v-for="q in quickQuestions"
            :key="q"
            class="text-[12px] px-3 py-1.5 rounded-full border cursor-pointer transition-colors"
            style="border-color: var(--semi-color-border); color: var(--semi-color-text-1);"
            @click="sendQuickQuestion(q)"
          >
            {{ q }}
          </button>
        </div>
      </div>

      <!-- 消息气泡 -->
      <div
        v-for="msg in messages"
        :key="msg.id"
        class="flex gap-3"
        :class="msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'"
      >
        <!-- 用户头像：有图片则显示图片，否则显示姓名首字母 -->
        <div v-if="msg.role === 'user'" class="avatar-icon shrink-0 mt-0.5 rounded-full overflow-hidden">
          <img
            v-if="userStore.userInfo?.avatar"
            :src="userStore.userInfo.avatar"
            :alt="userStore.userInfo.full_name || userStore.userInfo.username"
            style="width: 32px; height: 32px; display: block; object-fit: cover;"
          />
          <div v-else class="avatar-user w-full h-full flex items-center justify-center text-[13px] font-semibold text-white">
            {{ userInitial }}
          </div>
        </div>
        <!-- AI 头像 -->
        <div v-else class="avatar-icon avatar-bot shrink-0 mt-0.5 rounded-full flex items-center justify-center">
          <Icon name="heroicons:sparkles" class="w-4 h-4" />
        </div>

        <div
          class="max-w-[78%] px-4 py-2.5 rounded-2xl text-[13px] leading-relaxed whitespace-pre-wrap"
          :class="msg.role === 'user' ? 'msg-user rounded-tr-sm' : 'msg-bot rounded-tl-sm'"
        >
          {{ getMsgText(msg) }}
          <!-- 流式打字光标 -->
          <span
            v-if="msg.role === 'assistant' && status === 'streaming' && msg.id === messages.at(-1)?.id"
            class="typing-cursor"
          />
        </div>
      </div>

      <!-- 等待第一个 token（submitted 状态） -->
      <div v-if="status === 'submitted'" class="flex gap-3">
        <div class="avatar-icon avatar-bot shrink-0 mt-0.5 rounded-full flex items-center justify-center text-white">
          <Icon name="heroicons:sparkles" class="w-4 h-4" />
        </div>
        <div class="msg-bot px-4 py-3 rounded-2xl rounded-tl-sm">
          <div class="flex gap-1 items-center h-4">
            <span class="dot-bounce" style="animation-delay: 0ms;" />
            <span class="dot-bounce" style="animation-delay: 160ms;" />
            <span class="dot-bounce" style="animation-delay: 320ms;" />
          </div>
        </div>
      </div>

      <!-- 错误提示 -->
      <div v-if="error" class="flex justify-center">
        <div class="text-[12px] px-3 py-2 rounded-lg" style="background: var(--semi-color-danger-light-default); color: var(--semi-color-danger);">
          ⚠️ {{ error.message || 'AI 服务出错，请稍后重试' }}
        </div>
      </div>
    </div>

    <!-- ── 输入区域（row 2，永远贴底） ─────────────────── -->
    <div
      class="px-4 pt-3 pb-3"
      style="border-top: 1px solid var(--semi-color-border); background: var(--semi-color-bg-0);"
    >
      <div class="flex gap-2 items-end">
        <TextArea
          :value="input"
          :rows="1"
          :auto-size="{ minRows: 1, maxRows: 4 }"
          placeholder="输入问题，Enter 发送，Shift+Enter 换行..."
          class="flex-1"
          :disabled="isLoading"
          @change="(v: string) => (input = v)"
          @keydown="onKeydown"
        />
        <!-- 流式中显示停止按钮 -->
        <Button
          v-if="status === 'streaming'"
          theme="solid"
          type="warning"
          style="height: 32px; padding: 0 14px; min-width: 64px;"
          @click="chat.stop()"
        >
          停止
        </Button>
        <!-- 默认发送按钮 -->
        <Button
          v-else
          theme="solid"
          type="primary"
          :disabled="!input.trim() || isLoading"
          style="height: 32px; padding: 0 14px; min-width: 64px;"
          @click="handleSubmit"
        >
          发送
        </Button>
      </div>
    </div>

  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from "vue";
import { Chat } from "@ai-sdk/vue";
import { TextStreamChatTransport } from "ai";
import { Button, TextArea } from "@kousum/semi-ui-vue";
import { streamChat } from "@/api/ai";
import { useUserStore } from "@/stores/user";

const props = withDefaults(
  defineProps<{ initialQuery?: string }>(),
  { initialQuery: "" },
);

const userStore = useUserStore();
const userInitial = computed(() => {
  const name = userStore.userInfo?.full_name || userStore.userInfo?.username || "U";
  return name.charAt(0).toUpperCase();
});

// ── 会话 ID（多轮对话） ──────────────────────────────────
const conversationId = ref<string | undefined>(undefined);
const input = ref("");

// ── Chat 实例：使用 TextStreamChatTransport + 自定义 fetch ──
const chat = new Chat({
  transport: new TextStreamChatTransport({
    api: "/api/chat",
    fetch: async (_url, init) => {
      const body = JSON.parse((init?.body as string) ?? "{}");
      // v6 消息格式：parts 数组
      const msgs = body.messages as Array<{
        role: string;
        parts?: Array<{ type: string; text: string }>;
        content?: string;
      }>;
      const lastMsg = msgs?.at(-1);
      if (!lastMsg) return new Response("");

      const text =
        lastMsg.parts?.find((p) => p.type === "text")?.text ??
        lastMsg.content ??
        "";

      const stream = new ReadableStream({
        async start(controller) {
          const encoder = new TextEncoder();
          try {
            for await (const chunk of streamChat(text, conversationId.value)) {
              if (chunk.event === "message_end" && chunk.conversation_id) {
                conversationId.value = chunk.conversation_id;
              }
              if (chunk.answer) {
                controller.enqueue(encoder.encode(chunk.answer));
              }
            }
          } catch (err) {
            controller.error(err);
          } finally {
            controller.close();
          }
        },
      });

      return new Response(stream, {
        headers: { "Content-Type": "text/plain; charset=utf-8" },
      });
    },
  }),
});

// ── 响应式代理 Chat 内部 Vue refs ───────────────────────
const messages = computed(() => chat.messages);
const status = computed(() => chat.status);
const error = computed(() => chat.error);
const isLoading = computed(
  () => chat.status === "submitted" || chat.status === "streaming",
);

// 从 UIMessage parts 提取纯文本
function getMsgText(msg: { parts?: Array<{ type: string; text?: string }> }): string {
  if (msg.parts) {
    const tp = msg.parts.find((p) => p.type === "text");
    return tp?.text ?? "";
  }
  return "";
}

// ── 快捷问题 ────────────────────────────────────────────
const quickQuestions = [
  "查找2023年度财务档案",
  "人事档案保存期限规定",
  "如何申请档案利用？",
  "涉密档案处理流程",
];

// ── 发送消息 ────────────────────────────────────────────
async function handleSubmit() {
  const text = input.value.trim();
  if (!text || isLoading.value) return;
  input.value = "";
  await chat.sendMessage({ text });
}

async function sendQuickQuestion(q: string) {
  if (isLoading.value) return;
  await chat.sendMessage({ text: q });
}

// ── 初始问题（从首页携带） ──────────────────────────────
onMounted(() => {
  if (props.initialQuery.trim()) {
    chat.sendMessage({ text: props.initialQuery });
  }
});

// ── 键盘快捷键 ──────────────────────────────────────────
function onKeydown(e: KeyboardEvent) {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSubmit();
  }
}

// ── 自动滚动到底部 ──────────────────────────────────────
const scrollRef = ref<HTMLElement | null>(null);

watch(
  messages,
  async () => {
    await nextTick();
    if (scrollRef.value) {
      scrollRef.value.scrollTop = scrollRef.value.scrollHeight;
    }
  },
  { deep: true },
);
</script>

<style scoped>
/* 头像 */
.avatar-icon {
  width: 32px;
  height: 32px;
  min-width: 32px;
  color: #fff;
}
.avatar-user {
  background: var(--semi-color-primary);
}
.avatar-bot {
  background: var(--semi-color-tertiary-active);
}

/* 用户消息气泡 */
.msg-user {
  background: var(--semi-color-primary);
  color: #fff;
}

/* 助手消息气泡 */
.msg-bot {
  background: var(--semi-color-bg-2);
  color: var(--semi-color-text-0);
  border: 1px solid var(--semi-color-border);
}

/* 流式打字光标 */
.typing-cursor {
  display: inline-block;
  width: 2px;
  height: 13px;
  background: currentColor;
  margin-left: 2px;
  vertical-align: middle;
  animation: blink 0.9s step-end infinite;
}

/* 等待三点动画 */
.dot-bounce {
  display: inline-block;
  width: 6px;
  height: 6px;
  border-radius: 50%;
  background: var(--semi-color-text-2);
  animation: bounce 1.2s infinite ease-in-out;
}

@keyframes blink {
  0%, 100% { opacity: 1; }
  50% { opacity: 0; }
}

@keyframes bounce {
  0%, 80%, 100% { transform: translateY(0); }
  40% { transform: translateY(-6px); }
}
</style>
