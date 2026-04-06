<template>
  <footer class="mt-auto border-t border-base-300 bg-base-100 py-6">
    <div
      class="px-6 flex flex-col md:flex-row justify-between items-center text-sm text-base-content/60"
    >
      <p>
        &copy; {{ new Date().getFullYear() }} 智慧档案管理平台. 保留所有权利.
      </p>
      <div class="flex gap-6 mt-4 md:mt-0">
        <a href="#" class="hover:text-primary transition-colors">技术支持</a>
        <a href="#" class="hover:text-primary transition-colors">系统手册</a>
        <a href="#" class="hover:text-primary transition-colors">版本 2.0.1</a>
      </div>
    </div>
  </footer>
</template>
