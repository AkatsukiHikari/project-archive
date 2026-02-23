<template>
  <div
    class="grid grid-cols-1 md:grid-cols-2 lg:grid-cols-3 xl:grid-cols-6 gap-6"
  >
    <NuxtLink
      v-for="app in apps"
      :key="app.name"
      :to="app.href"
      class="group relative bg-base-100 rounded-xl p-6 shadow-card hover:shadow-soft-hover transition-all duration-300 border border-base-300 hover:border-primary/30 flex flex-col h-full"
    >
      <div
        class="h-14 w-14 rounded-lg flex items-center justify-center mb-4 group-hover:scale-110 transition-transform duration-300"
        :class="app.iconBg"
      >
        <Icon :name="app.icon" class="w-7 h-7" :class="app.iconColor" />
      </div>
      <h3
        class="text-lg font-semibold text-base-content mb-2 transition-colors"
        :class="app.hoverColor"
      >
        {{ app.name }}
      </h3>
      <p class="text-sm text-base-content/60 line-clamp-2">
        {{ app.description }}
      </p>
    </NuxtLink>
  </div>
</template>

<script setup lang="ts">
interface AppItem {
  name: string;
  description: string;
  icon: string;
  iconBg: string;
  iconColor: string;
  hoverColor: string;
  href: string;
}

defineProps<{
  apps: AppItem[];
}>();
</script>
