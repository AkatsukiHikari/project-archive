<template>
  <div class="flex flex-col space-y-6">
    <!-- 馆藏总量高亮卡 -->
    <DashboardCollectionOverview />

    <!-- AI 向量化进度 -->
    <CommonStatCard
      label="AI 向量化进度"
      value="87.2%"
      icon="heroicons:cpu-chip"
      icon-bg-class="bg-indigo-100 text-indigo-600 animate-pulse"
    >
      <div class="space-y-3">
        <div class="flex justify-between text-xs text-base-content/60">
          <span>本地档案库 RAG 索引构建中...</span>
          <span class="tabular-nums">12,450 / 14,280</span>
        </div>
        <CommonProgressBar :percent="87.2" bar-color="bg-indigo-500" animate />
        <div class="flex items-center gap-2 mt-2">
          <span class="h-2 w-2 rounded-full bg-green-500" />
          <span class="text-xs text-base-content/60">引擎状态: 运行正常</span>
        </div>
      </div>
    </CommonStatCard>
  </div>
</template>
