<template>
  <!-- 智慧档案平台 专属 Logo SVG —— 档案文件 + 折角设计 -->
  <svg
    :width="size"
    :height="size"
    viewBox="0 0 40 40"
    fill="none"
    xmlns="http://www.w3.org/2000/svg"
  >
    <!-- 蓝色圆角方形背景 -->
    <rect width="40" height="40" rx="9" fill="#1978e5" />
    <!-- 背景叠层文件 (堆叠感) -->
    <path
      d="M13 9 H23 L31 17 V32 a2 2 0 0 1 -2 2 H13 a2 2 0 0 1 -2 -2 V11 a2 2 0 0 1 2 -2Z"
      fill="white"
      fill-opacity="0.25"
    />
    <!-- 主文件体 -->
    <path
      d="M9 7 H21 L29 15 V31 a2 2 0 0 1 -2 2 H11 a2 2 0 0 1 -2 -2 V9 a2 2 0 0 1 2 -2Z"
      fill="white"
      fill-opacity="0.96"
    />
    <!-- 折角三角形 -->
    <path d="M21 7 L29 15 L21 15Z" fill="#1978e5" fill-opacity="0.22" />
    <!-- 文档内容线条 -->
    <rect x="12" y="19" width="12" height="2" rx="1" fill="#1978e5" fill-opacity="0.42" />
    <rect x="12" y="23" width="9" height="2" rx="1" fill="#1978e5" fill-opacity="0.42" />
    <rect x="12" y="27" width="11" height="2" rx="1" fill="#1978e5" fill-opacity="0.30" />
  </svg>
</template>

<script setup lang="ts">
withDefaults(
  defineProps<{
    size?: number | string;
  }>(),
  { size: 36 },
);
</script>
