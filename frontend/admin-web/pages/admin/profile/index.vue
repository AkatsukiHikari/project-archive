<template>
  <div class="min-h-screen bg-[var(--semi-color-bg-1)] py-8 px-6">
    <div class="max-w-5xl mx-auto flex gap-6 items-start">
      <!-- 左侧信息卡 + 导航 -->
      <aside class="w-64 shrink-0">
        <ProfileSidebarCard
          :display-name="displayName"
          :initial="initial"
          :job-title="profile?.job_title"
          :email="profile?.email"
          :phone="profile?.phone"
          :org-display="orgDisplay"
          :last-login-display="lastLoginDisplay"
          :avatar-src="avatarSrc"
          :uploading="avatarUploading"
          :roles="profile?.roles"
          :active-tab="activeTab"
          @upload-avatar="triggerUpload"
          @switch-tab="activeTab = $event"
        />
      </aside>

      <!-- 右侧内容区 -->
      <main class="flex-1 min-w-0">
        <ProfileBasicForm
          v-show="activeTab === 'basic'"
          :profile="profile"
          :loading="loading"
          @saved="onSaved"
        />
        <ProfileSecurity
          v-show="activeTab === 'security'"
          :last-login-display="lastLoginDisplay"
        />
        <ProfileTodos v-show="activeTab === 'todos'" />
        <ProfileAuditLog v-show="activeTab === 'audit'" />
      </main>
    </div>

    <!-- 隐藏头像上传 input -->
    <input
      ref="avatarInputRef"
      type="file"
      accept="image/jpeg,image/png,image/webp"
      class="hidden"
      @change="onAvatarChange"
    />
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from "vue";
import { Toast } from "@kousum/semi-ui-vue";
import { UserAPI, type User } from "@/api/iam";
import { useUserStore } from "@/stores/user";
import ProfileSidebarCard from "@/components/business/profile/ProfileSidebarCard.vue";
import ProfileBasicForm from "@/components/business/profile/ProfileBasicForm.vue";
import ProfileSecurity from "@/components/business/profile/ProfileSecurity.vue";
import ProfileTodos from "@/components/business/profile/ProfileTodos.vue";
import ProfileAuditLog from "@/components/business/profile/ProfileAuditLog.vue";

definePageMeta({ layout: "default" });

const userStore = useUserStore();
const loading = ref(true);
const profile = ref<User | null>(null);
const avatarSrc = ref("");
const avatarInputRef = ref<HTMLInputElement | null>(null);
const avatarUploading = ref(false);
const activeTab = ref("basic");

const displayName = computed(
  () => profile.value?.full_name || profile.value?.username || "用户",
);
const initial = computed(() => displayName.value.charAt(0).toUpperCase());
const orgDisplay = computed(() =>
  profile.value?.org_id ? "所属组织" : "未分配组织",
);
const lastLoginDisplay = computed(() =>
  profile.value?.last_login_time
    ? new Date(profile.value.last_login_time).toLocaleString("zh-CN")
    : "从未登录",
);

async function loadProfile() {
  // Pinia 快速通道，避免白屏
  if (userStore.userInfo?.avatar) avatarSrc.value = userStore.userInfo.avatar;
  try {
    const res = await UserAPI.getProfile();
    profile.value = res.data;
    if (res.data.avatar) avatarSrc.value = res.data.avatar;
    await userStore.getUserInfo();
  } finally {
    loading.value = false;
  }
}

function onSaved(user: User) {
  profile.value = user;
}

function triggerUpload() {
  avatarInputRef.value?.click();
}

async function onAvatarChange(e: Event) {
  const file = (e.target as HTMLInputElement).files?.[0];
  if (!file) return;
  if (file.size > 5 * 1024 * 1024) {
    Toast.error("头像不得超过 5MB");
    return;
  }
  const prev = avatarSrc.value;
  avatarSrc.value = URL.createObjectURL(file);
  avatarUploading.value = true;
  try {
    const res = await UserAPI.uploadAvatar(file);
    avatarSrc.value = res.data.avatar_url;
    if (profile.value) profile.value.avatar = res.data.avatar_url;
    await userStore.getUserInfo();
    Toast.success("头像更新成功");
  } catch {
    avatarSrc.value = prev;
    Toast.error("头像上传失败");
  } finally {
    avatarUploading.value = false;
    if (avatarInputRef.value) avatarInputRef.value.value = "";
  }
}

onMounted(loadProfile);
</script>
