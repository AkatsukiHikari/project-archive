<template>
  <div class="min-h-screen bg-slate-950 flex items-center justify-center">
    <div class="text-center space-y-4">
      <div class="loading loading-spinner loading-lg text-primary" />
      <p class="text-sm text-slate-400">正在完成登录...</p>
      <p v-if="error" class="text-sm text-red-400">{{ error }}</p>
    </div>
  </div>
</template>

<script setup lang="ts">
import { useAuth } from "@/hooks/useAuth";
import { useUserStore } from "@/stores/user";

definePageMeta({
  layout: false,
  middleware: [],
});

const route = useRoute();
const router = useRouter();
const { handleCallback, buildAuthorizeUrl } = useAuth();
const userStore = useUserStore();
const error = ref("");

const redirectToLogin = async () => {
  const url = await buildAuthorizeUrl("/");
  window.location.href = url;
};

onMounted(async () => {
  const code = route.query.code as string;

  if (!code) {
    error.value = "缺少授权码";
    setTimeout(redirectToLogin, 2000);
    return;
  }

  const ok = await handleCallback(code);
  if (ok) {
    // 拉取用户信息
    await userStore.getUserInfo();

    // 跳转到原始页面或首页
    const returnPath = sessionStorage.getItem("auth_return_path") || "/";
    sessionStorage.removeItem("auth_return_path");
    router.replace(returnPath);
  } else {
    error.value = "登录失败，正在重试...";
    setTimeout(redirectToLogin, 2000);
  }
});
</script>
