# 📝 动态联动功能更新说明

## ✨ 新增功能

### 1. **爬取类型联动** 🎯

根据选择的爬取类型，动态显示对应的输入框：

#### Search Mode（搜索模式）
- **输入框**: 关键词输入
- **特性**:
  - 支持标签显示（蓝色标签）
  - 每个关键词可单独删除（点击 × 按钮）
  - 多个关键词用逗号分隔
  - 实时预览已添加的关键词
  
```
关键词输入框
└─> [111 ×] [测试 ×] [爬虫 ×]  ← 标签形式展示
```

#### Detail Mode（详情模式）
- **输入框**: 帖子ID（多行文本框）
- **特性**:
  - 支持多行输入
  - 每行一个ID或用逗号分隔
  - 高度：80px

#### Creator Mode（创作者模式）
- **输入框**: 创作者ID/URL（多行文本框）
- **特性**:
  - 支持ID或完整URL
  - 等宽字体显示（便于查看URL）
  - 高度：96px
  - 示例提示：
    ```
    5533390220
    https://weibo.com/u/5533390220
    ```

### 2. **登录方式联动** 🔑

根据选择的登录方式，动态显示对应的配置：

#### QR Code Login（扫码登录）
- 显示提示：`扫码登录：启动后会弹出二维码窗口`
- 无额外输入框

#### Phone Login（手机号登录）
- 显示提示：`手机号登录：需要手动输入验证码`
- 无额外输入框

#### Cookie Login（Cookie登录）
- **显示**: Cookies 输入框（多行文本框）
- **特性**:
  - 高度：96px
  - 支持粘贴长文本
  - 提示文字：`在此粘贴 Cookies...`

### 3. **智能清空** 🧹

切换类型时自动清空相关字段：

```typescript
// 切换爬取类型时
Search → Detail:  清空 keywords，准备输入 specified_ids
Detail → Creator: 清空 specified_ids，准备输入 creator_ids
Creator → Search: 清空 creator_ids，准备输入 keywords

// 切换登录方式时
Cookie → QR Code: 清空 cookies（不需要了）
QR Code → Cookie: 保留之前的 cookies（如果有）
```

## 🎨 UI 改进

### 标签样式
```css
关键词标签:
- 背景: bg-blue-500/20
- 文字: text-blue-300
- 边框: border-blue-500/30
- 交互: hover:text-blue-100
```

### 文本框样式
```css
多行输入框:
- 统一样式和边框
- focus 时显示 ring-2
- 支持滚动条
- 禁用 resize（固定大小）
```

## 📐 组件更新

### TargetConfig.tsx
- ✅ 添加关键词标签展示
- ✅ Search Mode: 标签式关键词显示
- ✅ Detail Mode: 多行文本框
- ✅ Creator Mode: 多行文本框（等宽字体）
- ✅ 智能提示文字

### LoginConfig.tsx
- ✅ Cookie Login: Cookies 输入框
- ✅ 动态显示提示信息
- ✅ 根据登录方式切换 UI

### App.tsx
- ✅ 添加 `handleCrawlerTypeChange` 处理器
- ✅ 添加 `handleLoginTypeChange` 处理器
- ✅ 智能清空相关字段

## 🎯 使用示例

### 场景 1：搜索关键词
1. 选择 "Search Mode"
2. 输入 "美食,旅游,摄影"
3. 看到三个蓝色标签：[美食 ×] [旅游 ×] [摄影 ×]
4. 点击 × 可删除单个标签

### 场景 2：爬取创作者
1. 选择 "Creator Mode"
2. 输入框变为多行文本
3. 输入：
   ```
   5533390220
   https://weibo.com/u/5533390220
   ```
4. 等宽字体便于查看URL

### 场景 3：Cookie登录
1. 选择 "Cookie Login"
2. 出现 Cookies 输入框
3. 粘贴完整的 Cookie 字符串
4. 启动爬虫

## ⚡ 性能优化

- ✅ 使用 `useState` 避免不必要的重渲染
- ✅ 智能清空只影响相关字段
- ✅ 标签删除使用 `filter` 高效处理

## 🔄 切换流程

```
用户操作                    系统响应
──────────────────────────────────────────
选择 Search Mode    →    显示关键词输入框 + 标签
输入 "111,222"      →    显示 [111 ×] [222 ×]
切换到 Creator Mode →    清空关键词，显示创作者ID框
选择 Cookie Login   →    显示 Cookies 多行输入框
```

## 🎉 总结

这次更新实现了：
- ✅ 动态表单联动
- ✅ 智能字段清空
- ✅ 标签式关键词展示
- ✅ Cookie 输入支持
- ✅ 创作者 URL 输入优化
- ✅ 更好的用户体验

所有功能都按照参考截图的交互逻辑实现，确保用户体验流畅自然！

