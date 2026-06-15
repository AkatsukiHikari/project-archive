<template>
  <div class="rounded-xl p-6 overflow-auto" style="background:linear-gradient(160deg,#0f1830,#0a1020)">
    <!-- 透视舞台：rows 向纵深排列，columns 横向，每个货架按填充率着色 -->
    <div
      class="mx-auto"
      :style="{
        perspective: '1100px',
        width: 'fit-content',
      }"
    >
      <div
        class="flex flex-col gap-5"
        style="transform: rotateX(46deg) rotateZ(-2deg); transform-style: preserve-3d;"
      >
        <div
          v-for="r in rowList"
          :key="r"
          class="flex gap-3 justify-center"
        >
          <div
            v-for="shelf in shelvesByRow[r] ?? []"
            :key="shelf.id"
            class="relative rounded-sm transition-all duration-300 cursor-pointer"
            :style="shelfStyle(shelf)"
            :title="`${shelf.code} · ${shelf.used}/${shelf.capacity}（${pct(shelf)}%）`"
            @click="$emit('pick', shelf)"
          >
            <span
              class="absolute inset-x-0 -top-4 text-center text-[8px] font-mono"
              style="color:#5a6c9e;transform:rotateX(-46deg)"
            >{{ shelf.code }}</span>
          </div>
        </div>
      </div>
    </div>

    <!-- 图例 -->
    <div class="flex items-center justify-center gap-4 mt-6 text-[11px]" style="color:#7d93cf">
      <span class="flex items-center gap-1"><i class="w-3 h-3 rounded-sm inline-block" style="background:#1f3a5f" />空闲</span>
      <span class="flex items-center gap-1"><i class="w-3 h-3 rounded-sm inline-block" style="background:#2f7d6b" />正常</span>
      <span class="flex items-center gap-1"><i class="w-3 h-3 rounded-sm inline-block" style="background:#c79a3a" />较满</span>
      <span class="flex items-center gap-1"><i class="w-3 h-3 rounded-sm inline-block" style="background:#c2483f" />饱和</span>
      <span class="ml-2" style="color:#46598f">{{ rows }} 排 × {{ columns }} 列 · 共 {{ shelves.length }} 个架位（点击查看）</span>
    </div>
  </div>
</template>

<script setup lang="ts">
import { computed } from "vue";
import type { Shelf } from "@/api/storage";

const props = defineProps<{ shelves: Shelf[]; rows: number; columns: number }>();
defineEmits<{ pick: [Shelf] }>();

const rowList = computed(() => Array.from({ length: props.rows }, (_, i) => i));

const shelvesByRow = computed<Record<number, Shelf[]>>(() => {
  const map: Record<number, Shelf[]> = {};
  for (const s of props.shelves) {
    (map[s.row_index] ??= []).push(s);
  }
  for (const k of Object.keys(map)) {
    map[+k].sort((a, b) => a.col_index - b.col_index);
  }
  return map;
});

function pct(s: Shelf): number {
  return s.capacity ? Math.round((s.used / s.capacity) * 100) : 0;
}

function fillColor(p: number): string {
  if (p >= 90) return "#c2483f";
  if (p >= 70) return "#c79a3a";
  if (p > 0) return "#2f7d6b";
  return "#1f3a5f";
}

function shelfStyle(s: Shelf): Record<string, string> {
  const p = pct(s);
  const height = 14 + Math.round((p / 100) * 30); // 填充越高、立柱越高
  const color = fillColor(p);
  return {
    width: "30px",
    height: `${height}px`,
    background: `linear-gradient(180deg, ${color}, ${color}cc)`,
    boxShadow: `0 ${Math.round(height / 3)}px ${Math.round(height / 2)}px rgba(0,0,0,0.35), inset 0 1px 0 rgba(255,255,255,0.18)`,
    transform: `translateZ(${height / 2}px)`,
    border: "1px solid rgba(120,160,230,0.25)",
  };
}
</script>
