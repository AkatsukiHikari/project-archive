<template>
  <div
    class="h-full overflow-hidden"
    style="display:grid;grid-template-rows:1fr auto;background:var(--semi-color-bg-1)"
  >
    <!-- ── 消息列表 ─────────────────────────────────────────── -->
    <div ref="scrollRef" class="overflow-y-auto min-h-0 px-5 py-5 space-y-5">

      <!-- 欢迎态（无消息） -->
      <div
        v-if="chat.messages.length === 0 && chat.status === 'ready'"
        class="flex flex-col items-center justify-center h-full text-center gap-5"
      >
        <div class="w-16 h-16 rounded-2xl flex items-center justify-center" style="background:oklch(var(--p)/0.1)">
          <Icon name="heroicons:sparkles" class="w-8 h-8" style="color:oklch(var(--p))" />
        </div>
        <div>
          <p class="text-[15px] font-semibold mb-1" style="color:var(--semi-color-text-0)">有什么可以帮你？</p>
          <p class="text-[12px]" style="color:var(--semi-color-text-2)">可以询问档案内容、政策查阅、数据统计等</p>
        </div>
        <div class="flex flex-wrap gap-2 justify-center max-w-sm">
          <button
            v-for="q in QUICK_QUESTIONS"
            :key="q"
            class="text-[12px] px-3 py-1.5 rounded-full border cursor-pointer transition-colors hover:bg-[var(--semi-color-fill-0)]"
            style="border-color:var(--semi-color-border);color:var(--semi-color-text-1)"
            @click="() => chat.sendMessage({ text: q })"
          >
            {{ q }}
          </button>
        </div>
      </div>

      <!-- 消息气泡 -->
      <template v-for="msg in chat.messages" :key="msg.id">
        <div
          class="flex gap-3"
          :class="msg.role === 'user' ? 'flex-row-reverse' : 'flex-row'"
        >
          <!-- 用户头像 -->
          <div v-if="msg.role === 'user'" class="w-[30px] h-[30px] min-w-[30px] shrink-0 mt-0.5 rounded-full overflow-hidden">
            <img
              v-if="userStore.userInfo?.avatar"
              :src="userStore.userInfo.avatar"
              class="w-full h-full object-cover"
            >
            <div
              v-else
              class="w-full h-full flex items-center justify-center text-[12px] font-bold"
              style="background:oklch(var(--p));color:oklch(var(--pc))"
            >
              {{ userInitial }}
            </div>
          </div>

          <!-- AI 头像 -->
          <div
            v-else
            class="w-[30px] h-[30px] min-w-[30px] shrink-0 mt-0.5 rounded-full flex items-center justify-center"
            style="background:oklch(var(--p)/0.15);color:oklch(var(--p))"
          >
            <Icon name="heroicons:sparkles" class="w-3.5 h-3.5" />
          </div>

          <div
            class="max-w-[78%] px-4 py-2.5 rounded-2xl text-[13px] leading-relaxed whitespace-pre-wrap"
            :class="msg.role === 'user' ? 'rounded-tr-sm' : 'rounded-tl-sm'"
            :style="msg.role === 'user'
              ? 'background:oklch(var(--p));color:oklch(var(--pc))'
              : 'background:var(--semi-color-bg-0);color:var(--semi-color-text-0);border:1px solid var(--semi-color-border)'"
          >
            {{ getMsgText(msg) }}
            <span
              v-if="msg.role === 'assistant' && chat.status === 'streaming' && isLastMsg(msg)"
              class="typing-cursor"
            />
          </div>
        </div>
      </template>

      <!-- 等待第一个 token -->
      <div v-if="chat.status === 'submitted'" class="flex gap-3">
        <div
          class="w-[30px] h-[30px] min-w-[30px] shrink-0 mt-0.5 rounded-full flex items-center justify-center"
          style="background:oklch(var(--p)/0.15);color:oklch(var(--p))"
        >
          <Icon name="heroicons:sparkles" class="w-3.5 h-3.5" />
        </div>
        <div
          class="px-4 py-3 rounded-2xl rounded-tl-sm"
          style="background:var(--semi-color-bg-0);border:1px solid var(--semi-color-border)"
        >
          <div class="flex gap-1 items-center h-4">
            <span class="dot-bounce" style="animation-delay:0ms" />
            <span class="dot-bounce" style="animation-delay:160ms" />
            <span class="dot-bounce" style="animation-delay:320ms" />
          </div>
        </div>
      </div>

      <!-- 错误提示 -->
      <div v-if="chat.error" class="flex justify-center">
        <div
          class="flex items-center gap-1.5 text-[12px] px-3 py-2 rounded-lg"
          style="background:oklch(var(--er)/0.12);color:oklch(var(--er))"
        >
          <Icon name="heroicons:exclamation-triangle" class="w-3.5 h-3.5 shrink-0" />
          {{ chat.error.message }}
        </div>
      </div>
    </div>

    <!-- ── 输入区域 ─────────────────────────────────────────── -->
    <div
      class="px-4 pt-3 pb-3"
      style="border-top:1px solid var(--semi-color-border);background:var(--semi-color-bg-0)"
    >
      <div class="flex gap-2 items-end">
        <NInput
          v-model:value="inputValue"
          type="textarea"
          :autosize="{ minRows: 1, maxRows: 4 }"
          placeholder="输入问题，Enter 发送，Shift+Enter 换行…"
          class="flex-1"
          :disabled="chat.status !== 'ready'"
          @keydown="onKeydown"
        />
        <NButton
          v-if="chat.status === 'streaming'"
          type="warning"
          style="height:32px;padding:0 14px;min-width:64px"
          @click="() => chat.stop()"
        >
          停止
        </NButton>
        <NButton
          v-else
          type="primary"
          :disabled="!inputValue.trim() || chat.status !== 'ready'"
          style="height:32px;padding:0 14px;min-width:64px"
          @click="handleSubmit"
        >
          发送
        </NButton>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, watch, nextTick, onMounted } from "vue";
import { NButton, NInput } from "naive-ui";
import { Chat } from "@ai-sdk/vue";
import type { ChatTransport, UIMessage, UIMessageChunk } from "ai";
import { useUserStore } from "@/stores/user";

// ── 对外类型（父组件持久化用） ────────────────────────────────────────────────
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

// ── Props / Emits ──────────────────────────────────────────────────────────
const props = withDefaults(
  defineProps<{
    initialQuery?: string;
    initialMessages?: ChatMessage[];
    initialConversationId?: string;
  }>(),
  { initialQuery: "", initialMessages: () => [], initialConversationId: "" },
);

const emit = defineEmits<{
  "messages-updated": [messages: ChatMessage[], conversationId: string];
}>();

const userStore = useUserStore();

// ── Dify 错误友好化 ─────────────────────────────────────────────────────────
const parseDifyError = (raw: string | undefined): string => {
  if (!raw) return "AI 服务出错，请稍后重试";
  try {
    const p = (typeof raw === "string" ? JSON.parse(raw) : raw) as Record<string, unknown>;
    const errType = (p?.error_type ?? "") as string;
    const msg = ((p?.message ?? (p?.args as Record<string, unknown>)?.description ?? "") as string);
    if (errType === "InvokeError" || msg.includes("runner process has terminated") || msg.includes("llama")) {
      return "AI 模型暂时不可用，请稍后重试";
    }
    if (msg.includes("429") || msg.toLowerCase().includes("rate limit")) return "请求过于频繁，请稍后再试";
    if (msg.includes("401") || msg.toLowerCase().includes("api key")) return "AI 服务鉴权失败，请联系管理员";
    if (msg.includes("500") || msg.toLowerCase().includes("internal server")) return "AI 服务内部异常，请稍后重试";
    if (msg.length > 0 && msg.length <= 60 && !msg.startsWith("{")) return msg;
  } catch {
    if (typeof raw === "string" && raw.length <= 60 && !raw.startsWith("{")) return raw;
  }
  return "AI 服务出错，请稍后重试";
};

// ── Dify 传输层（适配 Dify SSE → AI SDK UIMessageChunk） ────────────────────
class DifyTransport implements ChatTransport<UIMessage> {
  conversationId: string;
  private readonly token: string;

  constructor(token: string, conversationId = "") {
    this.token = token;
    this.conversationId = conversationId;
  }

  sendMessages = async (options: Parameters<ChatTransport<UIMessage>["sendMessages"]>[0]): Promise<ReadableStream<UIMessageChunk>> => {
    const { messages, abortSignal } = options;
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    const query = lastUser?.parts.find((p): p is { type: "text"; text: string } => p.type === "text")?.text ?? "";

    const response = await fetch("/api/v1/ai/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.token}`,
      },
      body: JSON.stringify({ query, conversation_id: this.conversationId || null }),
      signal: abortSignal,
    });

    if (!response.ok) throw new Error(`AI 服务请求失败 (${response.status})`);

    return this.buildStream(response.body!);
  };

  reconnectToStream = async (): Promise<ReadableStream<UIMessageChunk> | null> => null;

  private buildStream = (body: ReadableStream<Uint8Array>): ReadableStream<UIMessageChunk> => {
    return new ReadableStream<UIMessageChunk>({
      start: async (controller) => {
        const reader = body.getReader();
        const decoder = new TextDecoder();
        let buffer = "";
        const textId = "txt";
        let closed = false;

        const safeClose = () => {
          if (closed) return;
          closed = true;
          try { controller.close(); } catch { /* already closed */ }
        };

        try {
          controller.enqueue({ type: "start" });
          controller.enqueue({ type: "text-start", id: textId });

          loop: while (true) {
            const { done, value } = await reader.read();
            if (done) break;

            buffer += decoder.decode(value, { stream: true });
            const lines = buffer.split("\n");
            buffer = lines.pop() ?? "";

            for (const line of lines) {
              if (!line.startsWith("data:")) continue;
              const json = line.slice(5).trim();
              if (!json) continue;
              try {
                const chunk = JSON.parse(json);

                if (chunk.event === "error") {
                  controller.enqueue({ type: "text-end", id: textId });
                  controller.enqueue({ type: "error", errorText: parseDifyError(chunk.message) });
                  controller.enqueue({ type: "finish" });
                  safeClose();
                  return;
                }

                if (chunk.event === "message_end") {
                  if (chunk.conversation_id) this.conversationId = chunk.conversation_id;
                  break loop;
                }

                if (chunk.answer) {
                  controller.enqueue({ type: "text-delta", id: textId, delta: chunk.answer });
                }
              } catch { /* skip non-JSON */ }
            }
          }

          controller.enqueue({ type: "text-end", id: textId });
          controller.enqueue({ type: "finish" });
        } catch (err) {
          if (!(err instanceof Error && err.name === "AbortError")) {
            try {
              controller.enqueue({ type: "text-end", id: textId });
              controller.enqueue({ type: "error", errorText: "AI 服务出错，请稍后重试" });
              controller.enqueue({ type: "finish" });
            } catch { /* ignore */ }
          }
        } finally {
          safeClose();
          reader.releaseLock();
        }
      },
    });
  };
}

// ── 格式转换 ────────────────────────────────────────────────────────────────
const toUIMsg = (msg: ChatMessage): UIMessage => ({
  id: msg.id,
  role: msg.role as "user" | "assistant",
  parts: [{ type: "text" as const, text: msg.content }],
});

const toSaved = (msg: UIMessage): ChatMessage => ({
  id: msg.id,
  role: msg.role as "user" | "assistant",
  content: msg.parts.find((p): p is { type: "text"; text: string } => p.type === "text")?.text ?? "",
});

// ── Chat 实例（@ai-sdk/vue 提供，内部使用 Vue ref 响应式状态） ──────────────
const transport = new DifyTransport(userStore.token ?? "", props.initialConversationId);

const chat = new Chat({
  transport,
  messages: props.initialMessages.map(toUIMsg),
});

// ── 辅助 ────────────────────────────────────────────────────────────────────
const userInitial = computed(() => {
  const name = userStore.userInfo?.full_name || userStore.userInfo?.username || "U";
  return name.charAt(0).toUpperCase();
});

const inputValue = ref("");
const scrollRef = ref<HTMLElement | null>(null);

const QUICK_QUESTIONS = [
  "查找2023年度财务档案",
  "人事档案保存期限规定",
  "如何申请档案利用？",
  "涉密档案处理流程",
];

const getMsgText = (msg: UIMessage) =>
  msg.parts.find((p): p is { type: "text"; text: string } => p.type === "text")?.text ?? "";

const isLastMsg = (msg: UIMessage) =>
  chat.messages[chat.messages.length - 1]?.id === msg.id;

// ── 自动滚动 ───────────────────────────────────────────────────────────────
watch(
  () => chat.messages,
  async () => {
    await nextTick();
    if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight;
  },
);

// ── 流结束后通知父组件持久化 ───────────────────────────────────────────────
watch(
  () => chat.status,
  (status, prev) => {
    if (status === "ready" && (prev === "streaming" || prev === "submitted")) {
      const saved = chat.messages.filter((m) => m.role !== "system").map(toSaved);
      emit("messages-updated", saved, transport.conversationId);
    }
  },
);

// ── 发送 ───────────────────────────────────────────────────────────────────
const handleSubmit = async () => {
  const text = inputValue.value.trim();
  if (!text || chat.status !== "ready") return;
  inputValue.value = "";
  await chat.sendMessage({ text });
};

const onKeydown = (e: KeyboardEvent) => {
  if (e.key === "Enter" && !e.shiftKey) {
    e.preventDefault();
    handleSubmit();
  }
};

// ── 初始 query ─────────────────────────────────────────────────────────────
onMounted(() => {
  if (props.initialQuery.trim()) chat.sendMessage({ text: props.initialQuery });
});
</script>

<style scoped>
.typing-cursor {
  display: inline-block; width: 2px; height: 13px;
  background: currentColor; margin-left: 2px;
  vertical-align: middle; animation: blink 0.9s step-end infinite;
}
.dot-bounce {
  display: inline-block; width: 5px; height: 5px; border-radius: 50%;
  background: var(--semi-color-text-2); animation: bounce 1.2s infinite ease-in-out;
}
@keyframes blink { 0%, 100% { opacity: 1; } 50% { opacity: 0; } }
@keyframes bounce { 0%, 80%, 100% { transform: translateY(0); } 40% { transform: translateY(-5px); } }
</style>
