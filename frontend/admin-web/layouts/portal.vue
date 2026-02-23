<template>
  <div
    class="bg-base-200 min-h-screen flex flex-col font-display text-base-content"
  >
    <LayoutAppHeader />
    <main
      class="flex-grow max-w-[1600px] mx-auto w-full px-4 sm:px-6 lg:px-8 py-8"
    >
      <slot />
    </main>
    <LayoutAppFooter />
  </div>
</template>
