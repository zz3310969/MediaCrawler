# 📊 数据管理功能说明

## ✨ 功能概述

数据管理功能提供了一个可视化的界面来浏览和管理爬取的数据文件。

## 🎯 如何打开

点击终端日志顶栏的 **"数据管理"** 按钮：

```
┌─────────────────────────────────────────┐
│ ●●● 系统控制台   [查记录] [数据管理] ← 点这里
└─────────────────────────────────────────┘
```

## 📐 弹窗布局

```
┌─────────────────────────────────────────────────┐
│  数据浏览器                    [重新扫描] [×]    │
│  数据文件管理  [6 条]                            │
├─────────────────────────────────────────────────┤
│  [全部(6)]  [Vip(1)]  [Contents(1)]  [Comments(1)]  │ ← 分类标签
├─────────────────────────────────────────────────┤
│  ┌──────────┐  ┌──────────┐  ┌──────────┐      │
│  │ 📄       │  │ 📄       │  │ 📄       │      │
│  │ file.json│  │ file.json│  │ file.json│      │
│  │ 11.81 KB │  │ 11.81 KB │  │ 129.48 KB│      │
│  │ 20 条    │  │ 20 条    │  │ 200 条   │      │
│  │ 2026/... │  │ 2026/... │  │ 2026/... │      │
│  │ [.JSON]  │  │ [.JSON]  │  │ [.JSON]  │      │
│  └──────────┘  └──────────┘  └──────────┘      │
└─────────────────────────────────────────────────┘
```

## 🎨 界面元素

### 1. 顶部标题栏
- **标题**：数据浏览器（青色）
- **副标题**：数据文件管理
- **统计徽章**：显示文件总数
- **重新扫描按钮**：刷新文件列表
- **关闭按钮**：右上角 × 关闭弹窗

### 2. 分类标签
- **全部**：显示所有文件
- **Vip**：VIP内容文件
- **Contents**：内容文件
- **Comments**：评论文件
- **Creator Contents**：创作者内容
- **Creator Creators**：创作者信息
- **数量统计**：每个分类显示文件数量

### 3. 文件卡片
每个文件卡片显示：
- 📄 **文件图标**（黄色）
- 📝 **文件名**（截断过长的名称）
- 📊 **文件大小** | **记录条数**（绿色）
- 🕐 **修改时间**
- 🏷️ **文件类型标签**（.JSON / .CSV / .EXCEL）
- 💾 **下载按钮**（悬停时显示）

## 🔍 功能特性

### 1. 自动分类
根据文件路径和名称自动分类：
- `weibo/json/_vip_contents_*.json` → **Vip**
- `*/json/_contents_*.json` → **Contents**
- `*/json/*_comments_*.json` → **Comments**
- `*/json/creator_content_*.json` → **Creator Contents**
- `*/json/creator_creator_*.json` → **Creator Creators**

### 2. 智能筛选
- 点击分类标签快速筛选文件
- 选中的分类显示青色高亮
- 显示当前分类的文件数量

### 3. 文件信息
- **文件大小**：自动转换单位（B/KB/MB）
- **记录条数**：JSON 文件显示数据条数
- **修改时间**：本地化时间格式
- **文件类型**：大写显示（.JSON / .CSV）

### 4. 下载功能
- 悬停文件卡片时显示下载按钮
- 点击下载按钮直接下载文件
- 使用浏览器原生下载

### 5. 响应式布局
- **大屏**：4列网格
- **中屏**：3列网格
- **小屏**：2列或1列

## 📡 API 接口

### 获取文件列表
```
GET /api/data/files
GET /api/data/files?platform=xhs
GET /api/data/files?file_type=json
```

**响应格式：**
```json
{
  "files": [
    {
      "name": "search_comments_2026-01-25.json",
      "path": "xhs/json/search_comments_2026-01-25.json",
      "size": 132591,
      "modified_at": 1769320815.5830705,
      "record_count": 200,
      "type": "json"
    }
  ]
}
```

### 下载文件
```
GET /api/data/download/{file_path}
```

## 🎯 使用流程

### 查看所有文件
1. 点击"数据管理"按钮
2. 默认显示"全部"分类
3. 查看所有爬取的数据文件

### 筛选特定类型
1. 点击分类标签（如"Comments"）
2. 只显示该类型的文件
3. 标签显示青色高亮

### 下载文件
1. 鼠标悬停在文件卡片上
2. 右下角出现下载按钮
3. 点击下载按钮保存文件

### 刷新列表
1. 点击右上角"重新扫描"按钮
2. 重新获取最新的文件列表
3. 按钮显示旋转动画

## 🎨 视觉特点

### 颜色方案
- **标题**：青色（`text-cyan-400`）
- **选中标签**：青色背景（`bg-cyan-500`）
- **文件图标**：黄色（`text-yellow-500`）
- **记录条数**：绿色（`text-green-500`）
- **类型标签**：黄色主题（`bg-yellow-500/10`）

### 交互效果
- **卡片悬停**：阴影加深（`hover:shadow-lg`）
- **标签悬停**：背景变色
- **下载按钮**：悬停时淡入显示
- **滚动区域**：最大高度 60vh，超出显示滚动条

## 🔧 技术实现

### 文件分类逻辑
```typescript
function extractCategory(filePath: string): string {
  // 从路径提取平台
  const match = filePath.match(/^([^/]+)\//)
  
  // 从文件名推断类型
  if (filePath.includes('vip_contents')) return 'Vip'
  if (filePath.includes('_contents_')) return 'Contents'
  if (filePath.includes('comments')) return 'Comments'
  // ...
}
```

### 统计计数
```typescript
const categoryCounts: Record<string, number> = {}
files.forEach(file => {
  const category = extractCategory(file.path)
  categoryCounts[category] = (categoryCounts[category] || 0) + 1
})
```

### 文件筛选
```typescript
const filteredFiles = selectedCategory === 'all' 
  ? files 
  : files.filter(file => extractCategory(file.path) === selectedCategory)
```

## 📱 响应式设计

```css
grid-cols-1           /* 小屏：1列 */
md:grid-cols-2        /* 中屏：2列 */
lg:grid-cols-3        /* 大屏：3列 */
xl:grid-cols-4        /* 超大屏：4列 */
```

## 🎉 完成！

现在你可以：
- ✅ 点击"数据管理"打开弹窗
- ✅ 查看所有爬取的数据文件
- ✅ 按类别筛选文件
- ✅ 查看文件详细信息
- ✅ 下载任意文件
- ✅ 重新扫描更新列表

立即体验这个强大的数据管理功能！🚀

