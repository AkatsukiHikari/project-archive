---
description: Frontend UI development rules - TailwindCSS + @kousum/semi-ui-vue
---

# 前端界面开发规范

本项目前端使用 **Nuxt 3 + TailwindCSS + @kousum/semi-ui-vue**。
所有 UI 开发必须遵循以下规则。不要使用 DaisyUI 和 Shadcn-vue 创建基础组件库。

---

## 一、样式规范

### 优先级（从高到低）

1. **Semi UI Vue 组件** — `<Button>`, `<Input>`, `<Table>`, `<Modal>`, `<Layout>` 等。不要重复造轮子，全面使用 Semi UI。
2. **TailwindCSS 工具类** — `flex`, `gap-4`, `p-4`, `w-full` 等，主要用于布局与间距控制。
3. **自定义 CSS** — 仅允许用于：复杂动画 `@keyframes`、第三方库样式覆盖、Tailwind 无法表达的极少数情况

### 禁止事项

- ❌ 在 `<style>` 中编写大量自定义 CSS
- ❌ 使用内联 `style` 属性
- ❌ 使用 `!important`（除非覆盖第三方库）
- ❌ 使用 DaisyUI 类名 (`btn`, `card` 等) 或依赖 shadcn-vue 生成的基础组件
- ❌ 使用 DaisyUI 类名 (`btn`, `card` 等) 或依赖 shadcn-vue 生成的基础组件

---

## 二、组件组织规范（Nuxt 风格）

### 目录结构

```
components/
├── layout/          # 布局组件（全局复用）
│   ├── AppHeader.vue
│   ├── AppFooter.vue
│   └── AppSidebar.vue
├── common/          # 通用 UI 组件（跨页面复用）
│   ├── SectionTitle.vue
│   ├── StatCard.vue
│   └── ProgressBar.vue
├── ui/              # shadcn-vue 基础组件
│   ├── Button.vue
│   ├── Dialog.vue
│   └── ...
├── dashboard/       # Dashboard 页面专属组件
│   ├── AppCardGrid.vue
│   └── WorkbenchPanel.vue
├── archive/         # 档案管理页面专属组件
└── iam/             # IAM 页面专属组件
```

### 规则

1. **Nuxt 自动导入**：`components/` 下所有 `.vue` 文件自动注册，无需手动 import
2. **命名规则**：Nuxt 自动按目录前缀注册 — `components/dashboard/AppCardGrid.vue` → `<DashboardAppCardGrid />`
3. **禁止在 `pages/` 下放组件**：`pages/` 的 `.vue` 文件会被注册为路由
4. **页面文件保持精简**：页面 `.vue` 只负责组合组件，不包含大段 HTML/逻辑
5. **组件单一职责**：每个组件不超过 150 行，超过的应拆分子组件

### 页面 vs 组件职责划分

```vue
<!-- ✅ 正确：pages/index.vue 只做组合 -->
<template>
  <div class="space-y-8">
    <CommonSectionTitle title="核心应用" />
    <DashboardAppCardGrid :apps="apps" />
    <div class="grid grid-cols-12 gap-8">
      <div class="col-span-8">
        <DashboardWorkbenchPanel />
      </div>
      <div class="col-span-4">
        <DashboardMetricsPanel />
      </div>
    </div>
  </div>
</template>

<!-- ❌ 错误：pages/index.vue 包含大量 HTML -->
<template>
  <div>
    <!-- 200+ 行 HTML 全写在这里 -->
  </div>
</template>
```

---

## 三、布局规范

### 多布局支持

```
layouts/
├── default.vue    # 管理后台布局（Sidebar + Header + Content）
├── portal.vue     # 门户首页布局（Header + Content + Footer，无侧边栏）
└── auth.vue       # 认证页布局（居中卡片样式，如登录页）
```

通过 `definePageMeta({ layout: 'portal' })` 指定页面使用哪个布局。

---

## 四、DaisyUI 常用组件速查

| 组件   | 类名                           | 场景     |
| ------ | ------------------------------ | -------- |
| 按钮   | `btn btn-primary btn-sm`       | 操作按钮 |
| 输入框 | `input input-bordered w-full`  | 表单输入 |
| 卡片   | `card bg-base-100 shadow-card` | 信息展示 |
| 统计   | `stat`                         | 数字指标 |
| 表格   | `table table-zebra`            | 数据列表 |
| 标签页 | `tabs tabs-bordered`           | 切换面板 |
| 徽章   | `badge badge-primary`          | 状态标记 |
| 菜单   | `menu`                         | 导航菜单 |
| 模态框 | `modal`                        | 弹框     |
| 下拉   | `dropdown`                     | 下拉菜单 |

---

## 五、图标规范

一律直接从 `@heroicons/vue` 导入并使用作为 Vue 组件，**严禁使用 Nuxt 提供的 `<Icon name="...">` 字符串形式**。所有的图标（即使结合 Semi UI 等第三方库）必须统一使用 `@heroicons/vue`。

```vue
<!-- ✅ 正确示范：直接引入并在 template 中使用 -->
<script setup>
import { ArchiveBoxIcon, MagnifyingGlassIcon } from "@heroicons/vue/24/outline";
</script>

<template>
  <ArchiveBoxIcon class="w-5 h-5 text-gray-500" />
</template>
```

```vue
<!-- ❌ 错误示范：使用 Nuxt Icon 或者其它字体图标库 -->
<Icon name="heroicons:archive-box" class="w-5 h-5" />
<Icon name="material-symbols:search" class="w-5 h-5" />
```

---

## 六、响应式设计

使用 Tailwind 断点：

- `sm:` ≥ 640px
- `md:` ≥ 768px
- `lg:` ≥ 1024px
- `xl:` ≥ 1280px

移动优先原则：默认写手机样式，用断点前缀添加桌面样式。

---

## 七、深色模式

- DaisyUI 主题通过 `<html data-theme="dark">` 切换
- Tailwind 通过 `dark:` 前缀添加深色样式
- 所有组件必须同时支持浅色/深色模式

---

## 八、API 数据对接

- 使用 `utils/axios/` 封装的 request 工具
- 标准响应格式：`{ code: 0, data: T, message: string }`
- 页面数据通过 `onMounted` + `ref` 加载（SPA 模式）
