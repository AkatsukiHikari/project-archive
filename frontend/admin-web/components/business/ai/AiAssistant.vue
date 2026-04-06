<template>
  <!-- 浮动触发按钮 -->
  <Teleport to="body">
    <!-- 触发按钮 -->
    <button
      class="fixed bottom-6 right-6 z-50 group"
      :title="open ? '关闭 AI 助手' : '打开 AI 档案助手'"
      @click="open = !open"
    >
      <!-- 脉冲光圈 -->
      <span
        v-if="!open"
        class="absolute inset-0 rounded-full bg-primary opacity-30 animate-ping pointer-events-none"
      />
      <span
        class="relative flex items-center justify-center w-14 h-14 rounded-full shadow-lg transition-all duration-300"
        :class="open ? 'bg-base-300 rotate-45' : 'bg-primary hover:scale-110'"
      >
        <Icon
          :name="open ? 'heroicons:x-mark' : 'heroicons:cpu-chip'"
          class="w-6 h-6 transition-colors"
          :class="open ? 'text-base-content' : 'text-primary-content'"
        />
      </span>
    </button>

    <!-- 弹出聊天窗口 -->
    <Transition
      enter-active-class="transition-all duration-300 ease-out"
      enter-from-class="opacity-0 translate-y-4 scale-95"
      leave-active-class="transition-all duration-200 ease-in"
      leave-to-class="opacity-0 translate-y-4 scale-95"
    >
      <div
        v-if="open"
        class="fixed bottom-24 right-6 z-50 w-[360px] rounded-2xl shadow-2xl border border-base-300 bg-base-100 flex flex-col overflow-hidden"
        style="max-height: 520px"
      >
        <!-- 顶栏 -->
        <div
          class="px-4 py-3 bg-gradient-to-r from-primary to-primary/80 flex items-center gap-3 shrink-0"
        >
          <div
            class="w-8 h-8 rounded-lg bg-white/20 flex items-center justify-center"
          >
            <Icon name="heroicons:sparkles" class="w-4 h-4 text-white" />
          </div>
          <div class="flex-1 min-w-0">
            <p class="text-sm font-semibold text-white leading-tight">
              档案 AI 助手
            </p>
            <p class="text-[10px] text-white/60">RAG 语义检索 · 全库档案</p>
          </div>
          <NuxtLink
            to="/ai"
            class="flex items-center gap-1 text-[11px] text-white/80 hover:text-white transition-colors bg-white/10 hover:bg-white/20 px-2.5 py-1 rounded-lg shrink-0"
            @click="open = false"
          >
            完整对话
            <Icon name="heroicons:arrow-top-right-on-square" class="w-3 h-3" />
          </NuxtLink>
        </div>

        <!-- 消息区（固定高度，内部滚动） -->
        <div
          ref="scrollRef"
          class="flex-1 overflow-y-auto p-4 flex flex-col gap-3 min-h-0"
          style="height: 340px"
        >
          <!-- 空状态 / 欢迎提示 -->
          <div
            v-if="!messages.length"
            class="flex flex-col gap-3 h-full items-start"
          >
            <!-- AI 欢迎泡 -->
            <div class="flex gap-2 items-start">
              <div
                class="w-6 h-6 rounded-full bg-primary/10 flex items-center justify-center shrink-0 mt-0.5"
              >
                <Icon name="heroicons:sparkles" class="w-3 h-3 text-primary" />
              </div>
              <div
                class="bg-base-200 text-sm px-3 py-2 rounded-2xl rounded-tl-sm text-base-content leading-relaxed"
              >
                您好！我是档案 AI 助手，可以帮您检索档案内容、查询政策法规。
              </div>
            </div>
            <!-- 快捷提问 -->
            <div class="flex flex-wrap gap-1.5 mt-1">
              <button
                v-for="q in QUICK"
                :key="q"
                class="text-xs border border-base-300 hover:border-primary hover:text-primary text-base-content/60 px-2.5 py-1 rounded-full transition-colors"
                @click="sendQuick(q)"
              >
                {{ q }}
              </button>
            </div>
          </div>

          <!-- 消息列表 -->
          <template v-else>
            <div
              v-for="(m, i) in messages"
              :key="i"
              class="flex gap-2"
              :class="m.role === 'user' ? 'flex-row-reverse' : 'flex-row'"
            >
              <div
                class="w-6 h-6 rounded-full shrink-0 flex items-center justify-center text-[10px] font-bold mt-0.5"
                :class="
                  m.role === 'user'
                    ? 'bg-primary text-primary-content'
                    : 'bg-base-200 text-base-content/60'
                "
              >
                <Icon
                  v-if="m.role === 'assistant'"
                  name="heroicons:sparkles"
                  class="w-3 h-3"
                />
                <span v-else>我</span>
              </div>
              <div
                class="max-w-[80%] text-xs px-3 py-2 rounded-2xl leading-relaxed whitespace-pre-wrap"
                :class="
                  m.role === 'user'
                    ? 'bg-primary text-primary-content rounded-tr-sm'
                    : 'bg-base-200 text-base-content rounded-tl-sm'
                "
              >
                <span v-if="m.loading" class="flex items-center gap-1">
                  <span
                    class="w-1 h-1 rounded-full bg-base-content/40 animate-bounce [animation-delay:0ms]"
                  />
                  <span
                    class="w-1 h-1 rounded-full bg-base-content/40 animate-bounce [animation-delay:150ms]"
                  />
                  <span
                    class="w-1 h-1 rounded-full bg-base-content/40 animate-bounce [animation-delay:300ms]"
                  />
                </span>
                <template v-else>{{ m.content }}</template>
              </div>
            </div>
          </template>
        </div>

        <!-- 输入栏 -->
        <div class="px-3 py-2.5 border-t border-base-300 bg-base-100 shrink-0">
          <div class="flex gap-2 items-center">
            <input
              v-model="input"
              type="text"
              placeholder="提问档案相关内容..."
              class="input input-sm input-bordered flex-1 text-xs focus:input-primary"
              :disabled="sending"
              @keydown.enter.prevent="send"
            />
            <button
              class="btn btn-primary btn-sm btn-square"
              :disabled="!input.trim() || sending"
              @click="send"
            >
              <Icon
                v-if="sending"
                name="heroicons:arrow-path"
                class="w-3.5 h-3.5 animate-spin"
              />
              <Icon
                v-else
                name="heroicons:paper-airplane"
                class="w-3.5 h-3.5"
              />
            </button>
          </div>
        </div>
      </div>
    </Transition>
  </Teleport>
</template>

<script setup lang="ts">
import { ref, nextTick } from "vue";

interface Message {
  role: "user" | "assistant";
  content: string;
  loading?: boolean;
}

const QUICK = ["查找档案", "保存期限规定", "申请借阅流程", "涉密处理规范"];

const open = ref(false);
const input = ref("");
const sending = ref(false);
const messages = ref<Message[]>([]);
const scrollRef = ref<HTMLElement | null>(null);

async function toBottom() {
  await nextTick();
  if (scrollRef.value) scrollRef.value.scrollTop = scrollRef.value.scrollHeight;
}

function sendQuick(q: string) {
  input.value = q;
  send();
}

async function send() {
  const text = input.value.trim();
  if (!text || sending.value) return;
  input.value = "";
  sending.value = true;
  messages.value.push({ role: "user", content: text });
  await toBottom();

  const placeholder: Message = {
    role: "assistant",
    content: "",
    loading: true,
  };
  messages.value.push(placeholder);
  await toBottom();

  try {
    // TODO: POST /api/v1/rag/chat  body: { question: text }
    await new Promise((r) => setTimeout(r, 1000));
    const idx = messages.value.lastIndexOf(placeholder);
    if (idx !== -1) {
      messages.value[idx] = {
        role: "assistant",
        content:
          "RAG 接口尚未接入，请点击「完整对话」进入 AI 页面使用完整功能。",
      };
    }
  } finally {
    sending.value = false;
    await toBottom();
  }
}
</script>
