<template>
  <div
    class="h-screen w-full flex flex-col items-center justify-center bg-base-200"
  >
    <div class="max-w-lg text-center p-8 bg-base-100 rounded-xl shadow-sm">
      <!-- 错误代码展示 -->
      <h1 class="text-9xl font-black text-base-content/10 select-none mb-4">
        {{ statusCode }}
      </h1>

      <!-- 错误标题 -->
      <h2 class="text-3xl font-bold text-base-content mb-4">
        {{ title }}
      </h2>

      <!-- 错误描述 -->
      <p class="text-base-content/60 mb-8 text-lg">
        {{ description }}
      </p>

      <!-- 操作按钮 -->
      <div class="flex justify-center gap-4">
        <button class="btn btn-primary px-8" @click="handleClear">
          <Icon name="heroicons:home" class="w-5 h-5 mr-2" />
          返回首页
        </button>

        <button class="btn btn-ghost px-8" @click="handleRefresh">
          <Icon name="heroicons:arrow-path" class="w-5 h-5 mr-2" />
          刷新页面
        </button>
      </div>

      <!-- 底部辅助信息 -->
      <div class="mt-12 text-sm text-base-content/40">
        <p v-if="error.message && statusCode === 500">
          错误详情: {{ error.message }}
        </p>
        <p class="mt-2">如果您认为这是一个系统故障，请联系系统管理员。</p>
      </div>
    </div>
  </div>
</template>

<script setup lang="ts">
import type { NuxtError } from "#app";

const props = defineProps({
  error: Object as () => NuxtError,
});

const statusCode = computed(() => props.error?.statusCode || 500);

const title = computed(() => {
  switch (statusCode.value) {
    case 403:
      return "访问被拒绝";
    case 404:
      return "页面未找到";
    case 500:
      return "服务器内部错误";
    default:
      return "发生未知错误";
  }
});

const description = computed(() => {
  switch (statusCode.value) {
    case 403:
      return "抱歉，您没有权限访问该页面。请联系管理员申请权限。";
    case 404:
      return "抱歉，您访问的页面不存在或已被移除。";
    case 500:
      return "服务器遇到了一个意外的情况，无法完成您的请求。";
    default:
      return props.error?.message || "系统运行遇到了一些问题。";
  }
});

const handleClear = () => {
  clearError({ redirect: "/" });
};

const handleRefresh = () => {
  window.location.reload();
};
</script>
