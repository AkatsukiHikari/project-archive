/**
 * DaisyUI 主题切换 Hook
 *
 * 功能：
 * - 提供可选主题列表（含预览色）
 * - 在 <html> 元素上设置 data-theme 属性
 * - 持久化到 localStorage，刷新后自动恢复
 */

export interface ThemeOption {
  name: string;
  label: string;
  dark: boolean; // 决定 Semi UI 是否切换到 dark mode
  colors: string[]; // 预览色块（primary, secondary, accent, base）
}

const STORAGE_KEY = "app-theme";

const themes: ThemeOption[] = [
  {
    name: "light",
    label: "明亮",
    dark: false,
    colors: ["#570df8", "#f000b8", "#37cdbe", "#ffffff"],
  },
  {
    name: "dark",
    label: "暗黑",
    dark: true,
    colors: ["#661ae6", "#d926a9", "#1fb2a6", "#191d24"],
  },
  {
    name: "coffee",
    label: "咖啡",
    dark: true,
    colors: ["#db924b", "#6f4e37", "#da8a67", "#20161f"],
  },
  {
    name: "aqua",
    label: "水蓝",
    dark: false,
    colors: ["#00cfd8", "#a991f7", "#f2d687", "#d3d3d3"],
  },
  {
    name: "night",
    label: "深夜",
    dark: true,
    colors: ["#38bdf8", "#818cf8", "#f471b5", "#0f172a"],
  },
  {
    name: "valentine",
    label: "玫瑰",
    dark: false,
    colors: ["#e96d7b", "#a991f7", "#66b1b3", "#fae8e8"],
  },
  {
    name: "lemonade",
    label: "柠檬",
    dark: false,
    colors: ["#519903", "#e9e92e", "#31b8b8", "#ffffff"],
  },
];

export function useTheme() {
  const currentTheme = useState<string>("app-theme", () => {
    if (import.meta.client) {
      return localStorage.getItem(STORAGE_KEY) || "light";
    }
    return "light";
  });

  /** 应用主题到 DOM */
  function applyTheme(theme: string) {
    if (import.meta.client) {
      // 1. 设置 DaisyUI 主题
      document.documentElement.setAttribute("data-theme", theme);

      // 2. 同步 Semi UI 明暗模式（Semi 只支持 dark/light 二值，无法匹配 DaisyUI 调色板）
      const isDark = themes.find((t) => t.name === theme)?.dark ?? false;
      if (isDark) {
        document.body.setAttribute("theme-mode", "dark");
      } else {
        document.body.removeAttribute("theme-mode");
      }
    }
  }

  /** 切换主题 */
  function setTheme(theme: string) {
    currentTheme.value = theme;
    applyTheme(theme);
    if (import.meta.client) {
      localStorage.setItem(STORAGE_KEY, theme);
    }
  }

  /** 初始化（在 onMounted 中调用） */
  function initTheme() {
    applyTheme(currentTheme.value);
  }

  return {
    currentTheme,
    themes,
    setTheme,
    initTheme,
  };
}
