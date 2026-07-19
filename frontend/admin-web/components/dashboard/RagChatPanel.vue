<template>
  <div
    class="h-full overflow-hidden"
    style="display:grid;grid-template-rows:1fr auto;background:var(--semi-color-bg-1)"
  >
    <!-- ── 消息列表 ─────────────────────────────────────────── -->
    <div ref="scrollRef" class="overflow-y-auto min-h-0 px-5 py-5 space-y-5">

      <!-- 欢迎态（无消息） —— 大卡片 + 示例问题 -->
      <div
        v-if="chat.messages.length === 0 && chat.status === 'ready'"
        class="flex flex-col items-center justify-center h-full text-center gap-6 px-6"
      >
        <div
          class="w-16 h-16 rounded-2xl flex items-center justify-center relative"
          style="background:linear-gradient(135deg, oklch(var(--p)/0.18), oklch(0.6 0.2 290/0.18));
                 box-shadow: 0 0 0 1px oklch(var(--p)/0.3) inset, 0 8px 30px oklch(var(--p)/0.2)"
        >
          <Icon name="heroicons:sparkles" class="w-8 h-8" style="color:oklch(var(--p))" />
        </div>
        <div>
          <p class="text-[16px] font-semibold mb-1.5" style="color:var(--semi-color-text-0)">让 AI 帮你检索档案库</p>
          <p class="text-[12px]" style="color:var(--semi-color-text-2)">支持 9 类档案业务场景 · 答案带可点引用 · 三档模型按需切换</p>
        </div>

        <!-- 3 张快捷示例卡 -->
        <div class="grid grid-cols-1 sm:grid-cols-3 gap-2.5 w-full max-w-2xl">
          <button
            v-for="card in SUGGESTION_CARDS"
            :key="card.q"
            class="text-left p-3 rounded-xl border cursor-pointer transition-all flex flex-col gap-1.5"
            style="border-color:var(--semi-color-border);background:var(--semi-color-bg-0)"
            @click="() => chat.sendMessage({ text: card.q })"
            @mouseenter="(e) => Object.assign((e.currentTarget as HTMLElement).style, { borderColor: 'oklch(var(--p))', boxShadow: '0 4px 16px oklch(var(--p)/0.12)', transform: 'translateY(-1px)' })"
            @mouseleave="(e) => Object.assign((e.currentTarget as HTMLElement).style, { borderColor: 'var(--semi-color-border)', boxShadow: 'none', transform: 'translateY(0)' })"
          >
            <div class="flex items-center gap-1.5">
              <Icon :name="card.icon" class="w-3.5 h-3.5" style="color:oklch(var(--p))" />
              <span class="text-[11px] font-medium" style="color:oklch(var(--p))">{{ card.tag }}</span>
            </div>
            <div class="text-[12.5px] leading-snug font-medium" style="color:var(--semi-color-text-0)">{{ card.q }}</div>
            <div class="text-[11px]" style="color:var(--semi-color-text-3)">{{ card.hint }}</div>
          </button>
        </div>

        <div class="text-[11px]" style="color:var(--semi-color-text-3)">
          或试试这些常见问题：
          <button
            v-for="q in QUICK_QUESTIONS"
            :key="q"
            class="mx-1 cursor-pointer underline border-none bg-transparent p-0 text-[11px]"
            style="color:oklch(var(--p))"
            @click="() => chat.sendMessage({ text: q })"
          >{{ q }}</button>
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

          <div class="max-w-[78%] flex flex-col gap-1.5" :class="msg.role === 'user' ? 'items-end' : 'items-start'">
            <div
              class="px-4 py-2.5 rounded-2xl text-[13px] leading-relaxed"
              :class="[msg.role === 'user' ? 'rounded-tr-sm' : 'rounded-tl-sm', msg.role === 'assistant' ? 'ai-answer markdown-body' : 'whitespace-pre-wrap']"
              :style="msg.role === 'user'
                ? 'background:oklch(var(--p));color:oklch(var(--pc))'
                : 'background:var(--semi-color-bg-0);color:var(--semi-color-text-0);border:1px solid var(--semi-color-border)'"
              @click="msg.role === 'assistant' && onAnswerClick($event)"
            >
              <template v-if="msg.role === 'assistant'">
                <template v-for="(part, pi) in answerParts(getMsgText(msg))" :key="pi">
                  <!-- eslint-disable-next-line vue/no-v-html -->
                  <div v-if="part.type === 'md'" v-html="renderAnswer(part.text)" />
                  <div
                    v-else-if="part.option"
                    class="my-2 rounded-xl px-1 py-2 w-full min-w-[280px] sm:min-w-[420px]"
                    style="background:var(--semi-color-fill-0)"
                  >
                    <EChart :option="themedChartOption(part.option)" :height="300" />
                  </div>
                  <div
                    v-else-if="part.pending"
                    class="flex items-center gap-2 my-2 text-[12px]"
                    style="color:var(--semi-color-text-2)"
                  >
                    <span class="dot-bounce" style="animation-delay:0ms" />
                    <span class="dot-bounce" style="animation-delay:160ms" />
                    图表生成中…
                  </div>
                  <div v-else class="my-2 text-[12px]" style="color:oklch(var(--er))">
                    图表配置解析失败，原始配置：
                    <pre class="mt-1 text-[11px] overflow-x-auto">{{ part.raw }}</pre>
                  </div>
                </template>
                <span v-if="chat.status === 'streaming' && isLastMsg(msg)" class="typing-cursor-inline" />
              </template>
              <template v-else>{{ getMsgText(msg) }}</template>
            </div>

            <!-- 引用 chip 行 —— 仅 AI 气泡下方展示 -->
            <div
              v-if="msg.role === 'assistant' && citationsFor(msg.id).length > 0"
              class="flex flex-col gap-1.5 mt-1"
            >
              <div class="flex items-center gap-1.5">
                <Icon name="heroicons:link" class="w-3 h-3" style="color:var(--semi-color-text-3)" />
                <span class="text-[10.5px] font-medium tracking-wide" style="color:var(--semi-color-text-3)">
                  {{ citationsFor(msg.id).length }} 条引用
                </span>
              </div>
              <div class="flex flex-wrap items-center gap-1.5">
                <NPopover
                  v-for="(chip, i) in citationsFor(msg.id)"
                  :key="chip.chunk_id + i"
                  trigger="hover"
                  placement="top"
                  :style="{ maxWidth: '360px' }"
                >
                  <template #trigger>
                    <button
                      class="flex items-center gap-1 px-2 py-0.5 rounded-full text-[11px] cursor-pointer transition-all border-none"
                      :style="chipStyle(chip)"
                      @click="onCitationClick(chip)"
                    >
                      <Icon :name="chipIcon(chip)" class="w-3 h-3" />
                      <span class="max-w-[180px] truncate">{{ chip.title }}</span>
                      <Icon
                        v-if="chip.source_type === 'meta' || chip.source_type === 'dify'"
                        name="heroicons:arrow-top-right-on-square"
                        class="w-2.5 h-2.5 opacity-60"
                      />
                    </button>
                  </template>
                  <div class="text-[12px] leading-relaxed flex flex-col gap-2">
                    <div class="flex items-center justify-between gap-2">
                      <span class="font-semibold" style="color:var(--semi-color-text-0)">{{ chip.title }}</span>
                      <NTag size="tiny" :bordered="false" :style="chipKindTagStyle(chip)">
                        {{ chipKindLabel(chip) }}
                      </NTag>
                    </div>
                    <div class="text-[11.5px] leading-relaxed" style="color:var(--semi-color-text-1)">
                      {{ chip.snippet || "（无摘要）" }}
                    </div>
                    <div class="flex items-center gap-2 text-[10.5px]" style="color:var(--semi-color-text-3)">
                      <span v-if="chip.score">相关度 {{ chip.score.toFixed(2) }}</span>
                      <span v-if="chip.extra?.source">· {{ chip.extra.source }}</span>
                      <span v-if="chip.extra?.version">· {{ chip.extra.version }}</span>
                    </div>
                    <button
                      v-if="chip.source_type === 'meta' || chip.source_type === 'dify'"
                      class="flex items-center gap-1 self-start text-[11px] cursor-pointer border-none bg-transparent p-0 font-medium"
                      style="color:oklch(var(--p))"
                      @click="onCitationClick(chip)"
                    >
                      <Icon name="heroicons:arrow-top-right-on-square" class="w-3 h-3" />
                      查看档案详情
                    </button>
                  </div>
                </NPopover>
              </div>
            </div>
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
import { useRouter } from "vue-router";
import { NButton, NInput, NPopover, NTag } from "naive-ui";
import { EChart } from "@/components/ui";
import { Chat } from "@ai-sdk/vue";
import type { ChatTransport, UIMessage, UIMessageChunk } from "ai";
import { marked } from "marked";
import DOMPurify from "dompurify";
import { useUserStore } from "@/stores/user";

// 配置 marked：GFM、换行保留、严格关闭以容忍 streaming 半截 markdown
marked.setOptions({
  gfm: true,
  breaks: true,
});

// ── 对外类型（父组件持久化用） ────────────────────────────────────────────────
export interface ChatMessage {
  id: string;
  role: "user" | "assistant";
  content: string;
}

// 引用 chip 数据形态 —— 兼容 Dify metadata.retriever_resources 与本系统 retrieve 输出
export interface CitationChip {
  chunk_id: string;
  source_type: "meta" | "rule" | "ocr" | "dify" | "unknown";
  source_id: string;   // archive_id / rule_id / document_id
  title: string;
  snippet: string;
  score: number;
  extra?: Record<string, unknown>;
}

// ── Props / Emits ──────────────────────────────────────────────────────────
const props = withDefaults(
  defineProps<{
    initialQuery?: string;
    initialMessages?: ChatMessage[];
    initialConversationId?: string;
    scenarioCode?: string;
    modelTier?: string;
    sessionId?: string;
  }>(),
  {
    initialQuery: "",
    initialMessages: () => [],
    initialConversationId: "",
    scenarioCode: "qa",
    modelTier: "",
    sessionId: "",
  },
);

const emit = defineEmits<{
  "messages-updated": [messages: ChatMessage[], conversationId: string, sessionId: string];
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
// 解析 Dify metadata.retriever_resources 与本系统 citations 两种形态
const normalizeCitations = (raw: unknown): CitationChip[] => {
  if (!Array.isArray(raw)) return [];
  return raw
    .map((item: unknown, i: number): CitationChip | null => {
      if (!item || typeof item !== "object") return null;
      const r = item as Record<string, unknown>;
      // 本系统形态
      if (r.chunk_id && r.source_type) {
        return {
          chunk_id: String(r.chunk_id),
          source_type: r.source_type as CitationChip["source_type"],
          source_id: String(r.source_id ?? ""),
          title: String(r.title ?? r.source_id ?? "引用"),
          snippet: String(r.snippet ?? ""),
          score: Number(r.score ?? 0),
          extra: (r.extra as Record<string, unknown>) ?? undefined,
        };
      }
      // Dify retriever_resources 形态
      const docName = r.document_name || r.dataset_name || `引用 ${i + 1}`;
      return {
        chunk_id: String(r.segment_id ?? r.document_id ?? `dify-${i}`),
        source_type: "dify",
        source_id: String(r.document_id ?? ""),
        title: String(docName),
        snippet: String(r.content ?? "").slice(0, 200),
        score: Number(r.score ?? 0),
      };
    })
    .filter((x): x is CitationChip => x !== null);
};

// agent_thought.observation 形如 {"pie_chart": "```echarts\n{...}\n```"}，
// 抽出全部 echarts 代码块内容（非图表工具的产出忽略）
const extractEchartsBlocks = (observation: string): string[] => {
  let parsed: Record<string, unknown>;
  try {
    parsed = JSON.parse(observation) as Record<string, unknown>;
  } catch {
    return [];
  }
  const blocks: string[] = [];
  for (const value of Object.values(parsed)) {
    if (typeof value !== "string") continue;
    for (const m of value.matchAll(/```echarts\s*([\s\S]*?)```/g)) {
      const inner = (m[1] ?? "").trim();
      if (inner) blocks.push(inner);
    }
  }
  return blocks;
};

class DifyTransport implements ChatTransport<UIMessage> {
  conversationId: string;
  sessionId: string;
  private readonly token: string;
  private scenarioCode: string;
  private modelTier: string;
  private readonly onCitations: (messageId: string, chips: CitationChip[]) => void;
  private lastAssistantId: string | null = null;

  constructor(
    token: string,
    conversationId = "",
    scenarioCode = "qa",
    modelTier = "",
    sessionId = "",
    onCitations: (messageId: string, chips: CitationChip[]) => void = () => {},
  ) {
    this.token = token;
    this.conversationId = conversationId;
    this.scenarioCode = scenarioCode;
    this.modelTier = modelTier;
    this.sessionId = sessionId;
    this.onCitations = onCitations;
  }

  setRouting = (scenarioCode: string, modelTier: string) => {
    this.scenarioCode = scenarioCode;
    this.modelTier = modelTier;
  };

  sendMessages = async (options: Parameters<ChatTransport<UIMessage>["sendMessages"]>[0]): Promise<ReadableStream<UIMessageChunk>> => {
    const { messages, abortSignal } = options;
    // 记录"本次回合"对应的 assistant 消息 id —— AI SDK 在 sendMessage 时已 push 占位
    const lastAssistant = [...messages].reverse().find((m) => m.role === "assistant");
    this.lastAssistantId = lastAssistant?.id ?? null;
    const lastUser = [...messages].reverse().find((m) => m.role === "user");
    const query = lastUser?.parts.find((p): p is { type: "text"; text: string } => p.type === "text")?.text ?? "";

    const response = await fetch("/api/v1/ai/chat", {
      method: "POST",
      headers: {
        "Content-Type": "application/json",
        Authorization: `Bearer ${this.token}`,
      },
      body: JSON.stringify({
        query,
        conversation_id: this.conversationId || null,
        scenario_code: this.scenarioCode || "qa",
        model_tier: this.modelTier || null,
        session_id: this.sessionId || null,
      }),
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
        // Agent 工具产出（echarts 图表块）藏在 agent_thought.observation 里，
        // 同一 thought 会被多次推送（先空后带结果），按 id 去重只注入一次
        const injectedThoughts = new Set<string>();

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

                // 后端首条 scenario_resolved 携带 session_id（uuid）
                if (chunk.event === "scenario_resolved" && chunk.session_id) {
                  this.sessionId = chunk.session_id;
                  continue;
                }

                if (chunk.event === "error") {
                  controller.enqueue({ type: "text-end", id: textId });
                  controller.enqueue({ type: "error", errorText: parseDifyError(chunk.message) });
                  controller.enqueue({ type: "finish" });
                  safeClose();
                  return;
                }

                if (chunk.event === "message_end") {
                  if (chunk.conversation_id) this.conversationId = chunk.conversation_id;
                  // 兼容两种引用形态：本系统直传 chunk.citations / Dify metadata.retriever_resources
                  const cits = normalizeCitations(
                    chunk.citations ?? chunk?.metadata?.retriever_resources,
                  );
                  if (cits.length > 0 && this.lastAssistantId) {
                    this.onCitations(this.lastAssistantId, cits);
                  }
                  break loop;
                }

                // Agent 模式：图表等工具产出在 agent_thought.observation，
                // 抽出 echarts 代码块按到达顺序注入正文（正好落在两轮 LLM 文字之间）
                if (chunk.event === "agent_thought") {
                  const tid = String(chunk.id ?? "");
                  const obs = String(chunk.observation ?? "");
                  if (tid && obs && !injectedThoughts.has(tid)) {
                    const blocks = extractEchartsBlocks(obs);
                    if (blocks.length > 0) {
                      injectedThoughts.add(tid);
                      for (const block of blocks) {
                        controller.enqueue({
                          type: "text-delta",
                          id: textId,
                          delta: `\n\n\`\`\`echarts\n${block}\n\`\`\`\n\n`,
                        });
                      }
                    }
                  }
                  continue;
                }

                // 后端独立推送的 citations 事件（P2 起后端在 Dify 之外注入）
                if (chunk.event === "citations" && this.lastAssistantId) {
                  const cits = normalizeCitations(chunk.citations);
                  if (cits.length > 0) this.onCitations(this.lastAssistantId, cits);
                  continue;
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

// 消息 → 引用列表（用 Map 不进 chat.messages，避免 SDK 状态污染）
const messageCitations = ref<Map<string, CitationChip[]>>(new Map());
const router = useRouter();

const onMessageCitations = (messageId: string, chips: CitationChip[]) => {
  // ES 命中的 meta 引用（带档号、可跳转查阅页）优先；
  // 不被随后 Dify 知识库召回的 dify 引用覆盖。
  const existing = messageCitations.value.get(messageId) ?? [];
  const existingHasMeta = existing.some((c) => c.source_type === "meta");
  const incomingHasMeta = chips.some((c) => c.source_type === "meta");
  if (existingHasMeta && !incomingHasMeta) return;
  messageCitations.value = new Map(messageCitations.value).set(messageId, chips);
};

const citationsFor = (id: string): CitationChip[] =>
  messageCitations.value.get(id) ?? [];

// AI 答案里的 markdown 链接（如 [题名](/archive/reader?id=xxx)）：
// 站内路径走 router.push；外部 http 链接才开新浏览器标签
const onAnswerClick = (e: MouseEvent) => {
  const anchor = (e.target as HTMLElement)?.closest("a");
  if (!anchor) return;
  const href = anchor.getAttribute("href") ?? "";
  if (!href || href.startsWith("#")) return;
  e.preventDefault();
  if (href.startsWith("/")) router.push(href);
  else window.open(href, "_blank", "noopener");
};

const onCitationClick = (chip: CitationChip) => {
  // meta 类（命中具体档案）→ 打开查阅页并按档号自动检索；无档号回退按题名检索
  if (chip.source_type === "meta") {
    const dh = (chip.extra?.DH as string) || "";
    router.push({
      path: "/service/reading",
      query: dh ? { DH: dh } : { q: chip.title },
    });
    return;
  }
  // dify 类（无具体 archive_id）→ 退回查阅页做关键字检索
  if (chip.source_type === "dify" && chip.title) {
    router.push({ path: "/service/reading", query: { q: chip.title } });
    return;
  }
  // rule / ocr 类不跳转（popover 已展示规则正文，无对应档案条目）
};

const chipStyle = (chip: CitationChip): Record<string, string> => {
  switch (chip.source_type) {
    case "meta":
    case "dify":
      return {
        background: "oklch(var(--p)/0.12)",
        color: "oklch(var(--p))",
        boxShadow: "0 0 0 1px oklch(var(--p)/0.28) inset",
      };
    case "rule":
      return {
        background: "oklch(0.95 0.05 290)",
        color: "oklch(0.4 0.18 290)",
        boxShadow: "0 0 0 1px oklch(0.55 0.2 290/0.4) inset",
      };
    case "ocr":
      return {
        background: "oklch(0.94 0.04 200)",
        color: "oklch(0.4 0.14 200)",
        boxShadow: "0 0 0 1px oklch(0.6 0.16 200/0.4) inset",
      };
    default:
      return {
        background: "var(--semi-color-fill-0)",
        color: "var(--semi-color-text-2)",
      };
  }
};

const chipIcon = (chip: CitationChip): string => {
  switch (chip.source_type) {
    case "meta":
    case "dify":
      return "heroicons:document-text";
    case "rule":
      return "heroicons:book-open";
    case "ocr":
      return "heroicons:photo";
    default:
      return "heroicons:link";
  }
};

const chipKindLabel = (chip: CitationChip): string => {
  switch (chip.source_type) {
    case "meta": return "档案元数据";
    case "rule": return "业务规则";
    case "ocr":  return "原文 OCR";
    case "dify": return "Dify 知识库";
    default:     return "未知来源";
  }
};

// 答案渲染：marked + DOMPurify，对 streaming 半截 markdown 容忍
function renderAnswer(text: string): string {
  if (!text) return "";
  // 把 《书名号》转成 marked 不会破坏的强调标记
  const preprocessed = text.replace(/《([^》]+)》/g, '<span class="ai-cite-title">《$1》</span>');
  let html: string;
  try {
    html = marked.parse(preprocessed, { async: false }) as string;
  } catch {
    html = preprocessed.replace(/\n/g, "<br/>");
  }
  // 回答里的〔档号〕转为查看原文链接（onAnswerClick 拦截站内 href 走 router.push）
  html = html.replace(
    /〔([A-Za-z0-9][\w-]{2,60})〕/g,
    '<a href="/archive/reader?id=$1">〔$1〕</a>',
  );
  // 清洗 HTML 防 XSS，保留 marked 生成的所有标签
  return DOMPurify.sanitize(html, {
    ADD_TAGS: ["span"],
    ADD_ATTR: ["class", "target", "rel"],
  });
}

// ── 答案分段：markdown 文本段 + echarts 图表段 ────────────────────────────────
type AnswerPart =
  | { type: "md"; text: string }
  | { type: "chart"; raw: string; pending: boolean; option?: Record<string, unknown> };

function answerParts(text: string): AnswerPart[] {
  const parts: AnswerPart[] = [];
  let rest = text;
  while (true) {
    const idx = rest.indexOf("```echarts");
    if (idx === -1) break;
    if (idx > 0) parts.push({ type: "md", text: rest.slice(0, idx) });
    const after = rest.slice(idx + "```echarts".length);
    const endIdx = after.indexOf("```");
    if (endIdx === -1) {
      // 流式中围栏未闭合 → 图表生成中占位
      parts.push({ type: "chart", raw: after.trim(), pending: true });
      return parts;
    }
    const raw = after.slice(0, endIdx).trim();
    let option: Record<string, unknown> | undefined;
    try {
      option = JSON.parse(raw) as Record<string, unknown>;
    } catch {
      option = undefined;
    }
    parts.push({ type: "chart", raw, pending: false, option });
    rest = after.slice(endIdx + 3);
  }
  if (rest) parts.push({ type: "md", text: rest });
  return parts;
}

// 图表主题适配：AI 生成的 option 不带颜色，按亮/暗主题补文字与轴线色
const { isDark } = useNaiveTheme();

type LooseObj = Record<string, unknown>;

function themedChartOption(raw: LooseObj): LooseObj {
  const text = isDark.value ? "#e5e7eb" : "#334155";
  const sub = isDark.value ? "#94a3b8" : "#64748b";
  const line = isDark.value ? "rgba(148,163,184,0.25)" : "rgba(100,116,139,0.2)";
  const opt = JSON.parse(JSON.stringify(raw)) as LooseObj;
  opt.backgroundColor = "transparent";
  opt.textStyle = { color: text, ...((opt.textStyle as LooseObj) ?? {}) };
  const title = opt.title as LooseObj | undefined;
  if (title && typeof title === "object") {
    opt.title = { ...title, textStyle: { color: text, fontSize: 14, ...((title.textStyle as LooseObj) ?? {}) } };
  }
  const legend = opt.legend as LooseObj | undefined;
  if (legend && typeof legend === "object") {
    opt.legend = { ...legend, textStyle: { color: sub, ...((legend.textStyle as LooseObj) ?? {}) } };
  }
  const themeAxis = (a: LooseObj): LooseObj => ({
    ...a,
    axisLabel: { color: sub, ...((a.axisLabel as LooseObj) ?? {}) },
    axisLine: { lineStyle: { color: line }, ...((a.axisLine as LooseObj) ?? {}) },
    splitLine: { lineStyle: { color: line }, ...((a.splitLine as LooseObj) ?? {}) },
  });
  for (const axisKey of ["xAxis", "yAxis"]) {
    const axis = opt[axisKey];
    if (!axis) continue;
    opt[axisKey] = Array.isArray(axis)
      ? (axis as LooseObj[]).map(themeAxis)
      : themeAxis(axis as LooseObj);
  }
  return opt;
}

const chipKindTagStyle = (chip: CitationChip): Record<string, string> => {
  switch (chip.source_type) {
    case "meta":
    case "dify":
      return { background: "oklch(var(--p)/0.12)", color: "oklch(var(--p))" };
    case "rule":
      return { background: "oklch(0.94 0.05 290)", color: "oklch(0.4 0.18 290)" };
    case "ocr":
      return { background: "oklch(0.94 0.04 200)", color: "oklch(0.4 0.14 200)" };
    default:
      return { background: "var(--semi-color-fill-0)", color: "var(--semi-color-text-2)" };
  }
};

// ── Chat 实例（@ai-sdk/vue 提供，内部使用 Vue ref 响应式状态） ──────────────
const transport = new DifyTransport(
  userStore.token ?? "",
  props.initialConversationId,
  props.scenarioCode,
  props.modelTier,
  props.sessionId ?? "",
  onMessageCitations,
);

const chat = new Chat({
  transport,
  messages: props.initialMessages.map(toUIMsg),
});

// 场景 / 模型档位变更时实时同步到 transport，下一条消息生效
watch(
  () => [props.scenarioCode, props.modelTier],
  ([scenario, tier]) => {
    transport.setRouting(scenario || "qa", tier || "");
  },
);

// ── 辅助 ────────────────────────────────────────────────────────────────────
const userInitial = computed(() => {
  const name = userStore.userInfo?.full_name || userStore.userInfo?.username || "U";
  return name.charAt(0).toUpperCase();
});

const inputValue = ref("");
const scrollRef = ref<HTMLElement | null>(null);

const QUICK_QUESTIONS = [
  "永久保管期限",
  "档号 DH 怎么组成",
  "干部任免",
  "财务凭证有哪些",
];

const SUGGESTION_CARDS = [
  {
    tag: "档案检索",
    icon: "heroicons:magnifying-glass",
    q: "查 2024 年度的财务凭证有哪些？",
    hint: "按年度 + 关键词检索真实档案",
  },
  {
    tag: "业务规则",
    icon: "heroicons:book-open",
    q: "永久保管档案和长期保管档案的区别？",
    hint: "30 条 DA/T 标准规则可查",
  },
  {
    tag: "档案解读",
    icon: "heroicons:sparkles",
    q: "档号 DH 字段的组成结构是什么？",
    hint: "字段定义 · 业务约定 · 操作说明",
  },
];

const getMsgText = (msg: UIMessage) =>
  msg.parts.find((p): p is { type: "text"; text: string } => p.type === "text")?.text ?? "";

const isLastMsg = (msg: UIMessage) =>
  chat.messages[chat.messages.length - 1]?.id === msg.id;

// ── 自动滚动 ───────────────────────────────────────────────────────────────
// 贴底才跟随：用户上滑看历史时不打扰；force=true 用于新消息加入时强制到底。
const scrollToBottom = (force = false) => {
  const el = scrollRef.value;
  if (!el) return;
  const nearBottom = el.scrollHeight - el.scrollTop - el.clientHeight < 120;
  if (force || nearBottom) el.scrollTop = el.scrollHeight;
};

// 最后一条消息的文本（流式增量时逐 token 变化，驱动跟随滚动）
const lastMsgText = computed(() => {
  const m = chat.messages[chat.messages.length - 1];
  return m ? getMsgText(m) : "";
});

// 新消息加入（用户提问 / AI 占位）→ 强制滚到底
watch(
  () => chat.messages.length,
  async () => {
    await nextTick();
    scrollToBottom(true);
  },
);

// 流式增量 + 状态切换 → 贴底时跟随
watch(
  () => [chat.status, lastMsgText.value],
  async () => {
    await nextTick();
    scrollToBottom();
  },
);

// ── 流结束后通知父组件持久化 ───────────────────────────────────────────────
watch(
  () => chat.status,
  (status, prev) => {
    if (status === "ready" && (prev === "streaming" || prev === "submitted")) {
      const saved = chat.messages.filter((m) => m.role !== "system").map(toSaved);
      emit("messages-updated", saved, transport.conversationId, transport.sessionId);
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

/* AI 答案区 markdown 渲染 */
.markdown-body :deep(p) {
  margin: 0.4em 0;
}
.markdown-body :deep(p:first-child) { margin-top: 0; }
.markdown-body :deep(p:last-child) { margin-bottom: 0; }
.markdown-body :deep(strong) {
  color: oklch(var(--p));
  font-weight: 600;
}
.markdown-body :deep(em) { font-style: italic; }
.markdown-body :deep(.ai-cite-title) {
  color: oklch(var(--p));
  font-weight: 500;
  background: oklch(var(--p)/0.08);
  padding: 0 3px;
  border-radius: 3px;
}
.markdown-body :deep(ul), .markdown-body :deep(ol) {
  margin: 0.4em 0;
  padding-left: 1.4em;
}
.markdown-body :deep(li) { margin: 2px 0; }
.markdown-body :deep(ul li::marker) { color: oklch(var(--p)/0.6); }
.markdown-body :deep(h1),
.markdown-body :deep(h2),
.markdown-body :deep(h3),
.markdown-body :deep(h4) {
  font-weight: 600;
  margin: 0.6em 0 0.3em;
  color: var(--semi-color-text-0);
}
.markdown-body :deep(h1) { font-size: 15px; }
.markdown-body :deep(h2) { font-size: 14px; }
.markdown-body :deep(h3), .markdown-body :deep(h4) { font-size: 13.5px; }
.markdown-body :deep(code) {
  font-family: ui-monospace, SFMono-Regular, Menlo, monospace;
  background: var(--semi-color-fill-0);
  padding: 1px 5px;
  border-radius: 4px;
  font-size: 12px;
  color: oklch(var(--p));
}
.markdown-body :deep(pre) {
  background: var(--semi-color-fill-0);
  padding: 10px 12px;
  border-radius: 8px;
  overflow-x: auto;
  margin: 0.5em 0;
  font-size: 12px;
  line-height: 1.5;
}
.markdown-body :deep(pre code) {
  background: transparent;
  padding: 0;
  color: var(--semi-color-text-0);
}
.markdown-body :deep(table) {
  border-collapse: collapse;
  margin: 0.5em 0;
  font-size: 12px;
  width: 100%;
}
.markdown-body :deep(th),
.markdown-body :deep(td) {
  border: 1px solid var(--semi-color-border);
  padding: 4px 8px;
  text-align: left;
}
.markdown-body :deep(th) {
  background: var(--semi-color-fill-0);
  font-weight: 600;
}
.markdown-body :deep(blockquote) {
  border-left: 3px solid oklch(var(--p)/0.4);
  padding-left: 10px;
  margin: 0.5em 0;
  color: var(--semi-color-text-2);
}
.markdown-body :deep(a) {
  color: oklch(var(--p));
  text-decoration: underline;
}
.markdown-body :deep(hr) {
  border: none;
  border-top: 1px solid var(--semi-color-border);
  margin: 0.6em 0;
}

/* 流式输出 cursor：跟在文字最后字符之后 */
.markdown-body :deep(.typing-cursor-inline) {
  display: inline-block;
  width: 2px;
  height: 1em;
  margin-left: 2px;
  background: oklch(var(--p));
  vertical-align: text-bottom;
  animation: blink 0.9s step-end infinite;
}
</style>
