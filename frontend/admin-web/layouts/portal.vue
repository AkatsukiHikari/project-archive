<template>
  <div
    class="bg-base-200 h-screen flex flex-col font-display text-base-content overflow-hidden"
  >
    <LayoutAppHeader />
    <main class="flex-1 min-h-0 w-full px-6 py-6 overflow-auto">
      <slot />
    </main>
    <LayoutAppFooter />
  </div>
</template>
