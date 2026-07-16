<template>
  <div class="flex items-center shrink-0 cursor-pointer" title="返回平台首页" @click="router.push('/')">
    <LogoIcon :size="28" class="shrink-0" />
    <div class="ml-2.5 hidden md:block">
      <div class="text-[13px] font-bold leading-tight whitespace-nowrap" style="color: var(--semi-color-text-0)">
        {{ title }}
      </div>
      <div class="text-[9px] tracking-widest uppercase mt-0.5" style="color: var(--semi-color-text-2)">
        {{ subtitle }}
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useRouter } from "vue-router";
import LogoIcon from "@/components/common/LogoIcon.vue";

defineProps<{ title: string; subtitle: string }>();
const router = useRouter();
</script>
