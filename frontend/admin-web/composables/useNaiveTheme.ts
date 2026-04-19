import { darkTheme, lightTheme } from "naive-ui";
import type { GlobalThemeOverrides } from "naive-ui";
import { computed } from "vue";
import { useTheme } from "@/hooks/useTheme";

/** DaisyUI 主题中属于暗色模式的主题名 */
const DARK_THEMES = new Set(["dark", "coffee", "night", "aqua"]);

/** 各 DaisyUI 主题对应的 primary 色（HEX，供 seemly 内部计算使用） */
const THEME_PRIMARY: Record<string, string> = {
  light:     "#1978e5",
  coffee:    "#C8813A",
  dark:      "#661ae6",
  aqua:      "#09ecf3",
  night:     "#38bdf8",
  valentine: "#e96d7b",
  lemonade:  "#519903",
};

function adjustHex(hex: string, amount: number): string {
  const r = parseInt(hex.slice(1, 3), 16);
  const g = parseInt(hex.slice(3, 5), 16);
  const b = parseInt(hex.slice(5, 7), 16);
  const adj = (c: number) =>
    amount > 0
      ? Math.min(255, Math.round(c + (255 - c) * amount))
      : Math.max(0, Math.round(c * (1 + amount)));
  return (
    "#" +
    [r, g, b]
      .map(adj)
      .map((v) => v.toString(16).padStart(2, "0"))
      .join("")
  );
}

/**
 * 构建主题覆盖。
 *
 * 关键约束：
 *   - `common` 中的颜色值会被 Naive UI 内部的 seemly/rgba() 解析处理，
 *     不能传入 CSS 变量字符串（如 oklch(var(--b1))），否则会报错。
 *     因此 `common` 仅保留 HEX 的 primary 色及非颜色属性。
 *   - 组件级别的覆盖（DataTable / Card / Modal / ...）是直接 merge 到
 *     最终 CSS 自定义属性，不经过 seemly 处理，
 *     因此可以安全地使用 DaisyUI CSS 变量引用（oklch(var(--b1)) 等）。
 *
 * DaisyUI v4 CSS 变量格式：`--b1: L% C H`（oklch 通道值）
 * 用法：oklch(var(--b1)) → 浏览器在运行时解析为实际颜色。
 */
function buildOverrides(primary: string): GlobalThemeOverrides {
  // DaisyUI CSS 变量桥（仅用于组件级覆盖，安全）
  const b1   = "oklch(var(--b1))";
  const b2   = "oklch(var(--b2))";
  const b2_5 = "oklch(var(--b2) / 0.5)";
  const bc   = "oklch(var(--bc))";
  const bc85 = "oklch(var(--bc) / 0.85)";
  const bc60 = "oklch(var(--bc) / 0.6)";
  const bc40 = "oklch(var(--bc) / 0.4)";
  const bc15 = "oklch(var(--bc) / 0.15)";
  const bc10 = "oklch(var(--bc) / 0.1)";
  const bc08 = "oklch(var(--bc) / 0.08)";
  const p    = "oklch(var(--p))";

  return {
    // ── common：只放 HEX 和非颜色属性 ─────────────────────────────────────
    common: {
      primaryColor:        primary,
      primaryColorHover:   adjustHex(primary, 0.15),
      primaryColorPressed: adjustHex(primary, -0.1),
      primaryColorSuppl:   adjustHex(primary, 0.2),
      borderRadius:        "6px",
      borderRadiusSmall:   "4px",
      fontFamily:          "Inter, system-ui, -apple-system, sans-serif",
    },

    // ── 按钮 ──────────────────────────────────────────────────────────────
    Button: {
      borderRadiusMedium: "6px",
      borderRadiusSmall:  "4px",
      borderRadiusLarge:  "8px",
    },

    // ── 输入框 ────────────────────────────────────────────────────────────
    Input: {
      borderRadius:     "6px",
      color:            b1,
      colorDisabled:    b2,
      textColor:        bc,
      textColorDisabled: bc40,
      placeholderColor:  bc40,
      border:           `1px solid ${bc15}`,
      borderHover:      `1px solid ${bc40}`,
      boxShadowFocus:   `0 0 0 2px ${primary}33`,
      caretColor:       p,
    },

    // ── 下拉选择 ──────────────────────────────────────────────────────────
    Select: { borderRadius: "6px" },

    // ── 卡片 ──────────────────────────────────────────────────────────────
    Card: {
      borderRadius:   "12px",
      color:          b1,
      colorModal:     b1,
      colorPopover:   b1,
      titleTextColor: bc,
      textColor:      bc85,
      borderColor:    bc10,
    },

    // ── 数据表格（核心融合点）────────────────────────────────────────────
    DataTable: {
      borderRadius:  "8px",

      // 表头
      thColor:            b2,
      thColorHover:       b2,
      thColorModal:       b2,
      thColorHoverModal:  b2,
      thColorPopover:     b2,
      thColorHoverPopover:b2,
      thTextColor:        bc,
      thFontWeight:       "600",

      // 表体
      tdColor:        b1,
      tdColorModal:   b1,
      tdColorPopover: b1,
      tdTextColor:    bc85,

      // 鼠标悬停
      tdColorHover:        b2,
      tdColorHoverModal:   b2,
      tdColorHoverPopover: b2,

      // 条纹行
      tdColorStriped:        b2_5,
      tdColorStripedModal:   b2_5,
      tdColorStripedPopover: b2_5,

      // 边框
      borderColor:        bc10,
      borderColorModal:   bc08,
      borderColorPopover: bc08,

      // 分页区域外边距
      paginationMargin:   "12px 16px 4px",
    },

    // ── 弹窗 ──────────────────────────────────────────────────────────────
    Modal: {
      borderRadius: "12px",
      color:        b1,
      textColor:    bc,
    },

    // ── 弹出层 ────────────────────────────────────────────────────────────
    Popover: {
      color:        b1,
      textColor:    bc,
      borderRadius: "8px",
    },

    // ── 侧边菜单 ──────────────────────────────────────────────────────────
    Menu: {
      borderRadius:              "6px",
      color:                     "transparent",
      itemTextColor:             bc60,
      itemTextColorHover:        bc,
      itemTextColorActive:       p,
      itemTextColorActiveHover:  p,
      itemTextColorChildActive:  p,
      itemColorHover:            bc08,
      itemColorActive:           `${primary}1e`,
      itemColorActiveHover:      `${primary}2e`,
      itemColorActiveCollapsed:  `${primary}1e`,
      groupTextColor:            bc40,
    },

    // ── 标签 ──────────────────────────────────────────────────────────────
    Tabs: {
      colorSegment:            b2,
      tabTextColorBar:         bc60,
      tabTextColorHoverBar:    bc,
      tabTextColorActiveBar:   p,
      tabTextColorDisabledBar: bc40,
      tabColorSegment:         b2,
      tabTextColorSegment:     bc60,
      tabTextColorHoverSegment:bc,
      tabTextColorActiveSegment: bc,
    },

    // ── 空状态 ────────────────────────────────────────────────────────────
    Empty: {
      textColor:     bc40,
      iconColor:     bc40,
    },

    // ── 分页 ──────────────────────────────────────────────────────────────
    Pagination: {
      itemTextColor:          bc60,
      itemTextColorHover:     bc,
      itemTextColorActive:    primary,
      itemColor:              b1,
      itemColorHover:         b2,
      itemBorderActive:       `1px solid ${primary}`,
      itemTextColorDisabled:  bc40,
      itemColorDisabled:      b2,
      inputColor:             b1,
      jumperTextColor:        bc60,
    },

    // ── 滚动条 ────────────────────────────────────────────────────────────
    Scrollbar: {
      color:       bc15,
      colorHover:  "oklch(var(--bc) / 0.25)",
    },

    // ── 对话框 ────────────────────────────────────────────────────────────
    Dialog: {
      color:          b1,
      textColor:      bc85,
      titleTextColor: bc,
      borderRadius:   "12px",
    },

    // ── 表单 ──────────────────────────────────────────────────────────────
    Form: {
      labelTextColor:       bc60,
      feedbackTextColorError: "oklch(var(--er))",
    },
  };
}

export function useNaiveTheme() {
  const { currentTheme } = useTheme();

  const isDark = computed(() => DARK_THEMES.has(currentTheme.value));
  const naiveTheme = computed(() => (isDark.value ? darkTheme : lightTheme));
  const themeOverrides = computed<GlobalThemeOverrides>(() =>
    buildOverrides(THEME_PRIMARY[currentTheme.value] ?? "#1978e5"),
  );

  return { naiveTheme, themeOverrides };
}
