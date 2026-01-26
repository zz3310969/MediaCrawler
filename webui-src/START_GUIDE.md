# 🚀 快速启动指南

## ✅ 项目已创建完成！

所有文件已经创建好，现在只需要安装依赖即可。

## 📦 第一步：安装依赖

```bash
cd /Users/zhengliangtian/Max/pyProjects/MediaCrawler/webui-src
npm install
```

这会安装所有必要的包，包括：
- React 18
- TypeScript
- Vite
- Tailwind CSS
- TanStack Query
- Axios
- Lucide Icons
- 等等...

## 🎨 第二步：启动开发服务器

### 方式 A：前后端分离开发（推荐）

**Terminal 1 - 启动后端：**
```bash
cd /Users/zhengliangtian/Max/pyProjects/MediaCrawler
uv run uvicorn api.main:app --port 8080 --reload
```

**Terminal 2 - 启动前端：**
```bash
cd /Users/zhengliangtian/Max/pyProjects/MediaCrawler/webui-src
npm run dev
```

然后访问：`http://localhost:5173`

✅ **优点：**
- 前端热更新，改代码立即生效
- 后端热重载
- 开发体验最佳

### 方式 B：构建后使用

```bash
# 1. 构建前端
cd /Users/zhengliangtian/Max/pyProjects/MediaCrawler/webui-src
npm run build

# 2. 启动后端（包含前端）
cd ..
uv run uvicorn api.main:app --port 8080
```

然后访问：`http://localhost:8080`

✅ **优点：**
- 只需要一个服务
- 模拟真实生产环境

## 📁 项目结构

```
webui-src/
├── src/
│   ├── api/                     # API 接口
│   │   ├── client.ts           # Axios 配置
│   │   └── crawler.ts          # 爬虫 API
│   ├── components/              # 组件
│   │   ├── ui/                 # UI 组件
│   │   ├── CrawlerControl.tsx  # 控制面板
│   │   └── LogViewer.tsx       # 日志查看器
│   ├── hooks/                   # Hooks
│   │   └── useWebSocket.ts     # WebSocket
│   ├── lib/                     # 工具函数
│   ├── App.tsx                  # 主应用
│   ├── main.tsx                 # 入口
│   └── index.css                # 样式
├── public/                      # 静态资源
├── index.html                   # HTML 模板
├── vite.config.ts              # Vite 配置
├── tailwind.config.js          # Tailwind 配置
├── tsconfig.json               # TypeScript 配置
└── package.json                # 依赖配置
```

## 🎯 功能说明

### 左侧 - 爬虫控制面板
- ✅ 平台选择（小红书、抖音、B站等）
- ✅ 登录方式（扫码、手机号、Cookie）
- ✅ 爬取类型（搜索、详情、创作者）
- ✅ 动态表单（根据类型显示不同输入）
- ✅ 高级选项（评论、二级评论、无头模式）
- ✅ 实时状态显示

### 右侧 - 实时日志
- ✅ WebSocket 实时推送
- ✅ 颜色分级（info/success/warning/error）
- ✅ 导出日志
- ✅ 清空日志
- ✅ 自动滚动

## 🛠️ 开发命令

```bash
# 启动开发服务器
npm run dev

# 构建生产版本（输出到 ../api/webui）
npm run build

# 预览构建结果
npm run preview

# 代码检查
npm run lint
```

## 🎨 技术亮点

1. **TypeScript 类型安全**：所有 API 调用都有类型检查
2. **实时通信**：WebSocket 实时日志推送
3. **状态管理**：TanStack Query 自动管理 API 状态
4. **响应式设计**：支持不同屏幕尺寸
5. **深色主题**：科技感的 Command Center 风格
6. **性能优化**：Vite 快速构建，React 18 新特性

## 🐛 常见问题

### Q: npm install 速度慢？

A: 可以使用国内镜像：
```bash
npm config set registry https://registry.npmmirror.com
npm install
```

### Q: 端口被占用？

A: 修改 `vite.config.ts` 中的 `server.port`

### Q: WebSocket 连接失败？

A: 确保后端已启动在 8080 端口，检查控制台错误信息

### Q: API 请求 404？

A: 确认后端服务正在运行，检查 `vite.config.ts` 的代理配置

## 📚 下一步

1. ✅ 安装依赖: `npm install`
2. ✅ 启动开发: `npm run dev`
3. 🎯 查看效果: `http://localhost:5173`
4. 🚀 开始开发或构建部署

## 💡 提示

- 开发时推荐使用 VS Code + TypeScript + ESLint 插件
- 修改代码后会自动热更新，无需刷新页面
- 构建前确保没有 TypeScript 错误
- 生产部署只需要构建后的 `../api/webui` 目录

---

**开始你的开发之旅吧！** 🎉

