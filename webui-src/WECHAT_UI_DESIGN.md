# 微信公众号爬虫界面重构设计方案

## 1. 设计目标
- **专属工作台体验**：将微信公众号爬虫从通用配置中剥离，提供更符合公众号运营特性的独立工作区。
- **所见即所得**：在同一界面集成了"配置"、"执行"与"数据预览"，让用户能实时看到爬取成果。
- **数据可视化**：直接展示爬取到的文章列表、阅读量等数据，而不仅是下载文件。

## 2. 布局设计 (两栏式布局)

采用经典的 **左侧控制 / 右侧数据** 布局：

- **左侧控制栏 (Sidebar)** - 宽度 320px
  - **状态头**：显示当前登录状态 (Cookie 有效性)。
  - **模式选择**：搜索 / 公众号 / 文章 / 合集 (Tab 切换)。
  - **参数配置**：根据模式动态变化的输入区。
  - **高级选项**：折叠式的抓取选项 (评论/阅读量/正文)。
  - **执行控制**：醒目的开始/停止按钮，及实时进度条。

- **右侧工作区 (Workspace)** - 自适应宽度
  - **数据概览 (Dashboard)**：显示今日抓取数量、总阅读量等关键指标卡片。
  - **数据浏览器 (Data Explorer)**：
    - 表格形式展示抓取的文章。
    - 列包含：标题、公众号、发布时间、阅读量、点赞、在看、评论数。
    - 支持按关键词过滤、按阅读量排序。
    - 支持直接导出选中的数据。
  - **实时日志 (Live Log)**：在抓取进行时自动切换或分屏显示日志。

## 3. 数据交互流程
1. **自动登录状态检测**：
   - 界面加载时自动检测 Cookie 状态，若失效提示扫码。
   - 扫码成功后自动刷新状态。
2. **任务与数据联动**：
   - 爬虫运行时，右侧实时追加新抓取到的数据行 (需后端 WebSocket 支持推送数据对象，目前仅推送日志)。
   - *当前阶段方案*：爬虫结束后，自动刷新数据列表；或提供"刷新"按钮读取最新的 JSON 结果文件。

## 4. 数据展示设计细节
- **文章列表**：
  - 标题列支持点击跳转原文。
  - 阅读量 > 10w+ 高亮显示。
  - 支持多选批量操作 (导出/删除)。
- **多账号管理**：
  - 如果支持多账号 Cookie，可在左上角切换当前使用的微信账号。

## 5. 组件结构规划

```tsx
// WeChatDashboard.tsx
<div className="flex h-screen">
  <WeChatSidebar /> // 左侧控制
  <WeChatWorkspace /> // 右侧数据与日志
</div>

// WeChatSidebar
<Card>
  <ModeTabs /> // 模式切换
  <ConfigForm /> // 输入表单
  <LoginStatus /> // 登录状态
  <ControlPanel /> // 开始/停止/进度
</Card>

// WeChatWorkspace
<Tabs defaultValue="data">
  <TabsList>
    <TabsTrigger value="data">数据管理</TabsTrigger>
    <TabsTrigger value="log">运行日志</TabsTrigger>
    <TabsTrigger value="stats">统计图表</TabsTrigger>
  </TabsList>
  <TabsContent value="data">
    <DataExplorer /> // 数据表格
  </TabsContent>
  <TabsContent value="log">
    <TerminalLog /> // 复用现有组件
  </TabsContent>
</Tabs>
```

## 6. 后需后端支持 (Future Work)
- **API `/api/wechat/articles`**: 分页获取已爬取的文章数据 (目前是存文件的，需要一个读取文件并解析为 JSON 列表的接口)。
- **API `/api/wechat/login_status`**: 更精确的登录状态检测。

