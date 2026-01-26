# 🎨 主题切换功能说明

## ✨ 功能概述

MediaCrawler WebUI 现在支持三种主题模式：
- ☀️ **Light** - 浅色主题
- 🌙 **Dark** - 深色主题（默认）
- 💻 **Auto** - 自动跟随系统

## 📍 位置

主题切换按钮位于**右上角导航栏**：

```
┌─────────────────────────────────────────────┐
│ 🕷️ MediaCrawler  [Star]    [☀️ Light ▼] ← 这里 │
└─────────────────────────────────────────────┘
```

## 🎯 使用方法

### 1. 点击主题按钮
点击右上角的主题按钮（显示当前主题）

### 2. 选择主题
弹出下拉菜单，显示三个选项：
```
┌─────────────────┐
│ ☀️ Light    ✓   │ ← 当前选中（青色高亮）
│ 🌙 Dark         │
│ 💻 Auto         │
└─────────────────┘
```

### 3. 切换生效
- 点击任意选项立即切换
- 主题偏好自动保存到 localStorage
- 下次打开自动恢复上次的选择

## 🎨 三种模式详解

### ☀️ Light Mode（浅色模式）
- **背景**：浅灰色渐变（slate-50 → slate-100）
- **卡片**：白色背景
- **文字**：深色文字
- **适合**：明亮环境、日间使用

### 🌙 Dark Mode（深色模式）
- **背景**：深灰色渐变（slate-950 → slate-900）
- **卡片**：深色背景
- **文字**：浅色文字
- **适合**：暗光环境、夜间使用
- **默认主题**

### 💻 Auto Mode（自动模式）
- **跟随系统**：根据操作系统的主题自动切换
- **智能适配**：白天 Light，晚上 Dark
- **无需手动**：系统改变时自动更新

## 🔧 技术实现

### 主题状态管理
```typescript
const [theme, setTheme] = useState<Theme>(() => {
  const saved = localStorage.getItem('theme') as Theme
  return saved || 'dark'  // 默认深色
})
```

### 主题切换逻辑
```typescript
useEffect(() => {
  const root = document.documentElement
  
  if (theme === 'auto') {
    // 自动模式：检测系统主题
    const isDark = window.matchMedia('(prefers-color-scheme: dark)').matches
    root.classList.toggle('dark', isDark)
  } else {
    // 手动模式：应用选择的主题
    root.classList.toggle('dark', theme === 'dark')
  }
  
  localStorage.setItem('theme', theme)
}, [theme])
```

### CSS 变量
```css
:root {
  /* Light 模式变量 */
  --background: 0 0% 100%;
  --foreground: 222.2 84% 4.9%;
  ...
}

.dark {
  /* Dark 模式变量 */
  --background: 222.2 84% 4.9%;
  --foreground: 210 40% 98%;
  ...
}
```

## 🎨 UI 适配

所有组件都使用 Tailwind 的 `dark:` 前缀实现主题适配：

### 示例
```tsx
// 背景色
className="bg-white dark:bg-slate-950"

// 文字颜色
className="text-slate-900 dark:text-white"

// 边框颜色
className="border-slate-200 dark:border-slate-800"
```

## 📐 下拉菜单样式

### 按钮状态
- **未展开**：显示当前主题图标和名称
- **悬停**：背景变亮，文字高亮
- **展开**：显示下拉菜单

### 菜单样式
- **背景**：深色半透明（`bg-slate-800`）
- **选中项**：青色背景（`bg-cyan-500/10`）+ 勾选图标
- **悬停**：背景变亮（`hover:bg-slate-700/50`）
- **图标**：每个选项左侧显示对应图标

## 🎯 完整交互流程

```
1. 点击 [☀️ Light ▼]
   ↓
2. 显示下拉菜单：
   ┌──────────────────┐
   │ ☀️ Light    ✓    │
   │ 🌙 Dark          │
   │ 💻 Auto          │
   └──────────────────┘
   ↓
3. 点击 "Dark"
   ↓
4. 页面立即切换到深色主题
   ↓
5. 按钮显示 [🌙 Dark ▼]
   ↓
6. 偏好保存到 localStorage
```

## 💾 持久化

主题选择会保存到浏览器的 localStorage：
- **Key**: `theme`
- **Value**: `'light'` | `'dark'` | `'auto'`
- **默认**: `'dark'`

刷新页面或重新打开，会自动恢复上次的主题选择。

## 🌟 特色功能

1. **✅ 三种模式**：Light / Dark / Auto
2. **✅ 图标标识**：☀️ / 🌙 / 💻
3. **✅ 勾选显示**：当前选中项显示 ✓
4. **✅ 智能适配**：Auto 模式跟随系统
5. **✅ 持久化**：自动保存用户偏好
6. **✅ 即时生效**：点击立即切换
7. **✅ 全局适配**：所有组件都支持
8. **✅ 平滑过渡**：切换时有过渡动画

## 🎊 完成！

现在你可以：
- ✅ 点击右上角的主题按钮
- ✅ 选择 Light / Dark / Auto
- ✅ 看到整个界面立即切换主题
- ✅ 刷新页面保持你的选择

主题切换功能已经完美集成！🎉

