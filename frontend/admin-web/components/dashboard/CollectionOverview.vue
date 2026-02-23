<template>
  <div
    class="bg-gradient-to-br from-primary to-blue-600 rounded-xl p-6 shadow-soft text-white relative overflow-hidden"
  >
    <!-- 装饰图标 -->
    <div
      class="absolute right-0 top-0 opacity-10 transform translate-x-1/4 -translate-y-1/4"
    >
      <Icon name="heroicons:folder" class="w-36 h-36" />
    </div>
    <div class="relative z-10">
      <p class="text-blue-100 text-sm font-medium mb-1">馆藏总量</p>
      <h3 class="text-3xl font-bold font-display tracking-tight">1,240,592</h3>
      <div class="flex items-center mt-4 text-xs font-medium text-blue-100">
        <span
          class="bg-white/20 px-2 py-0.5 rounded mr-2 flex items-center gap-1"
        >
          <Icon name="heroicons:arrow-trending-up" class="w-3.5 h-3.5" />
          +2.4%
        </span>
        <span>较上月</span>
      </div>
    </div>
  </div>
</template>
