# MediaCrawler WebUI

MediaCrawler 的现代化 Web 用户界面，基于 React + TypeScript + Vite 构建。

## 技术栈

- ⚛️ React 18
- 📘 TypeScript
- ⚡ Vite
- 🎨 Tailwind CSS
- 🧩 自定义 UI 组件
- 🔄 TanStack Query (React Query)
- 🌐 WebSocket 实时通信
- 🎭 Lucide Icons

## 快速开始

### 安装依赖

```bash
npm install
```

### 开发模式

```bash
npm run dev
```

前端会启动在 `http://localhost:5173`，并自动代理 API 请求到 `http://localhost:8080`

### 构建生产版本

```bash
npm run build
```

构建产物会输出到 `../api/webui` 目录，可以直接通过 Python 后端访问。

## 项目结构

```
src/
├── api/              # API 接口封装
│   ├── client.ts     # Axios 客户端
│   └── crawler.ts    # 爬虫 API
├── components/       # React 组件
│   ├── ui/          # UI 基础组件
│   ├── CrawlerControl.tsx  # 爬虫控制面板
│   └── LogViewer.tsx       # 日志查看器
├── hooks/           # 自定义 Hooks
│   └── useWebSocket.ts     # WebSocket Hook
├── lib/             # 工具函数
│   └── utils.ts
├── App.tsx          # 根组件
├── main.tsx         # 入口文件
└── index.css        # 全局样式
```

## 功能特性

- ✅ 爬虫配置和控制
- ✅ 实时状态监控
- ✅ WebSocket 实时日志
- ✅ 深色主题
- ✅ 响应式设计
- ✅ TypeScript 类型安全

## 开发说明

1. 确保后端已启动: `uv run uvicorn api.main:app --port 8080`
2. 启动前端开发服务器: `npm run dev`
3. 访问 `http://localhost:5173` 进行开发

## 部署

```bash
# 构建前端
npm run build

# 启动后端（包含前端）
cd ..
uv run uvicorn api.main:app --port 8080

# 访问 http://localhost:8080
```

