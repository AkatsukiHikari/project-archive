<template>
  <div
    class="bg-base-100 rounded-xl p-6 shadow-card border border-base-300 flex flex-col justify-between flex-grow"
  >
    <div class="flex justify-between items-start mb-4">
      <div>
        <p class="text-base-content/60 text-sm font-medium mb-1">
          四性检测合格率
        </p>
        <h3 class="text-3xl font-bold text-base-content font-display">98.5%</h3>
      </div>
      <div class="p-2 bg-purple-100 rounded-lg text-purple-600">
        <Icon name="heroicons:adjustments-horizontal" class="w-5 h-5" />
      </div>
    </div>
    <div class="space-y-3">
      <CommonProgressBar
        :percent="100"
        label="可用性"
        bar-color="bg-primary"
        height="sm"
      />
      <CommonProgressBar
        :percent="99.2"
        label="完整性"
        bar-color="bg-primary opacity-80"
        height="sm"
      />
      <CommonProgressBar
        :percent="96.3"
        label="安全性"
        bar-color="bg-primary opacity-60"
        height="sm"
      />
    </div>
  </div>
</template>
