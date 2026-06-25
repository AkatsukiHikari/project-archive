<template>
  <div
    class="relative h-full w-full overflow-hidden flex items-center justify-center"
    style="background:
      radial-gradient(circle at 20% 20%, oklch(var(--p)/0.08), transparent 55%),
      radial-gradient(circle at 80% 60%, oklch(0.6 0.18 290/0.07), transparent 55%),
      var(--semi-color-bg-0);"
  >
    <!-- 装饰光晕（纯装饰）-->
    <div class="absolute inset-0 pointer-events-none opacity-60">
      <div
        class="absolute top-1/2 left-1/2 -translate-x-1/2 -translate-y-1/2 w-[420px] h-[420px] rounded-full blur-3xl animate-[pulse_5s_ease-in-out_infinite]"
        style="background:radial-gradient(circle, oklch(var(--p)/0.18), transparent 70%)"
      />
    </div>

    <div class="relative z-10 max-w-md flex flex-col items-center gap-5 px-8 py-10 text-center">
      <div
        class="w-16 h-16 rounded-2xl flex items-center justify-center"
        style="background:linear-gradient(135deg, oklch(var(--p)/0.16), oklch(0.6 0.2 290/0.16));
               box-shadow:0 0 0 1px oklch(var(--p)/0.3) inset, 0 8px 30px oklch(var(--p)/0.18);"
      >
        <Icon :name="iconName" class="w-7 h-7" style="color:oklch(var(--p))" />
      </div>

      <div class="space-y-2">
        <h2 class="text-[18px] font-semibold tracking-tight" style="color:var(--semi-color-text-0)">
          {{ scenario?.name || 'AI 能力' }}
        </h2>
        <p
          class="text-[12.5px] leading-relaxed"
          style="color:var(--semi-color-text-2)"
        >{{ scenario?.description || '该能力正在调试中，敬请期待' }}</p>
      </div>

      <!-- 进度状态条（视觉占位）-->
      <div class="w-full">
        <div
          class="relative h-1.5 w-full rounded-full overflow-hidden"
          style="background:oklch(var(--p)/0.08)"
        >
          <div
            class="absolute inset-y-0 left-0 rounded-full animate-[shimmer_2.4s_ease-in-out_infinite]"
            :style="{
              width: `${progress}%`,
              background: 'linear-gradient(90deg, oklch(var(--p)/0.6), oklch(0.65 0.2 290/0.8))'
            }"
          />
        </div>
        <div class="mt-2 flex items-center justify-between text-[11px]" style="color:var(--semi-color-text-3)">
          <span>AI 能力解锁中</span>
          <span>{{ phaseLabel }}</span>
        </div>
      </div>

      <div
        class="flex items-center gap-2 px-3 py-1.5 rounded-full text-[11.5px]"
        style="background:oklch(var(--p)/0.08); color:oklch(var(--p))"
      >
        <Icon name="heroicons:sparkles" class="w-3 h-3" />
        预计 {{ etaPhase }} 上线
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";

interface ScenarioInfo {
  code: string;
  name: string;
  description?: string;
}

interface Props {
  scenario: ScenarioInfo | null;
}
const props = defineProps<Props>();

// 设计稿 §4：四期路线图 — 把每个能力的预期上线期写死，避免空喊
const PHASE_BY_CODE: Record<string, { phase: string; eta: string; progress: number }> = {
  qa:        { phase: "P1 / P2", eta: "P1",  progress: 70 },
  search:    { phase: "P2",      eta: "P2",  progress: 40 },
  summary:   { phase: "P2",      eta: "P2",  progress: 35 },
  kb_manage: { phase: "P2 / P3", eta: "P2",  progress: 30 },
  attach:    { phase: "P3",      eta: "P3",  progress: 20 },
  catalog:   { phase: "P3",      eta: "P3",  progress: 18 },
  fournat:   { phase: "P4",      eta: "P4",  progress: 10 },
  draft:     { phase: "P4",      eta: "P4",  progress: 10 },
  relate:    { phase: "P4",      eta: "P4",  progress: 8 },
};

const meta = computed(() => PHASE_BY_CODE[props.scenario?.code ?? ""] ?? { phase: "—", eta: "后续", progress: 12 });
const phaseLabel = computed(() => meta.value.phase);
const etaPhase   = computed(() => meta.value.eta);
const progress   = computed(() => meta.value.progress);

const iconName = computed(() => {
  const m: Record<string, string> = {
    qa: "heroicons:chat-bubble-bottom-center-text",
    search: "heroicons:magnifying-glass",
    summary: "heroicons:document-text",
    attach: "heroicons:link",
    catalog: "heroicons:rectangle-stack",
    kb_manage: "heroicons:book-open",
    fournat: "heroicons:shield-check",
    draft: "heroicons:pencil-square",
    relate: "heroicons:share",
  };
  return m[props.scenario?.code ?? ""] ?? "heroicons:sparkles";
});
</script>

<style scoped>
@keyframes shimmer {
  0%   { transform: translateX(-30%); opacity: 0.7; }
  50%  { transform: translateX(0);    opacity: 1;   }
  100% { transform: translateX(30%);  opacity: 0.7; }
}
</style>
