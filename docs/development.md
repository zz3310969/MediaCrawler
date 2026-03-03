# 开发指南

## 1. 环境搭建

### 前置依赖

- **Python** >= 3.11
- **Node.js** >= 16.0.0（抖音、知乎平台需要）
- **uv**（推荐的 Python 包管理工具）：[安装指南](https://docs.astral.sh/uv/getting-started/installation)

### 安装步骤

```bash
# 克隆项目
git clone <repo-url>
cd MediaCrawler

# 安装 Python 依赖
uv sync

# 安装 Playwright 浏览器驱动
uv run playwright install
```

> 也可以用 Python 原生 venv，但不推荐。参见 README.md 中的备选方案。

---

## 2. 运行爬虫（命令行模式）

```bash
# 搜索模式 - 关键词搜索小红书笔记
uv run main.py --platform xhs --lt qrcode --type search

# 详情模式 - 按 ID 爬取指定帖子
uv run main.py --platform xhs --lt qrcode --type detail

# 创作者模式 - 爬取创作者主页
uv run main.py --platform xhs --lt qrcode --type creator

# 查看所有参数
uv run main.py --help
```

### 常用参数

| 参数 | 说明 | 可选值 |
|------|------|--------|
| `--platform` | 目标平台 | xhs, dy, ks, bili, wb, tieba, zhihu, wechat |
| `--lt` | 登录方式 | qrcode, phone, cookie |
| `--type` | 爬虫模式 | search, detail, creator |
| `--save_data_option` | 存储方式 | csv, json, excel, sqlite, db, postgres, mongodb |
| `--init_db` | 初始化数据库 | sqlite, mysql, postgres |

### 配置修改

主要配置在 `config/base_config.py`，有详细中文注释。修改关键词、爬取数量、是否爬评论等都在这里。

---

## 3. WebUI 开发

WebUI 由后端 API（FastAPI）和前端（React）组成。

### 启动后端

```bash
# 方式一：uvicorn 启动（支持热重载）
uv run uvicorn api.main:app --port 8080 --reload

# 方式二：模块方式
uv run python -m api.main
```

启动后访问 `http://localhost:8080` 打开 WebUI。

### 前端开发

```bash
cd webui-src

# 安装依赖
npm install

# 开发模式（热更新）
npm run dev

# 生产构建（输出到 api/webui/）
npm run build
```

### 前端技术栈

- React 18 + TypeScript
- Vite 构建
- TailwindCSS 样式
- Radix UI 组件库
- WebSocket 实时通信

### 前端目录结构

```
webui-src/src/
├── pages/           # 页面：Login, Dashboard, Tasks, TaskCreate, DataManagement...
├── components/      # 组件：按功能分目录（common, layout, tasks, data...）
├── api/             # API 调用封装
├── hooks/           # React Hooks（useApi, useTasks, useWebSocket...）
├── types/           # TypeScript 类型定义
├── lib/             # 工具函数
└── mock/            # Mock 数据
```

### API 与 Worker

- **API 进程**：处理 HTTP/WebSocket 请求，管理任务状态
- **Worker 进程**：执行爬虫任务，可独立启动

开发时可以设置 `INTEGRATED_WORKER=1` 让 API 和 Worker 在同一进程运行。

---

## 4. 数据库

### 初始化

```bash
# SQLite（推荐本地开发）
uv run main.py --init_db sqlite

# MySQL
uv run main.py --init_db mysql

# PostgreSQL
uv run main.py --init_db postgres
```

### 配置

数据库连接配置在 `config/db_config.py`：

```python
# SQLite
SQLITE_DB_PATH = "database/sqlite_tables.db"

# MySQL
MYSQL_DB_HOST = "localhost"
MYSQL_DB_PORT = 3306
MYSQL_DB_NAME = "media_crawler"

# PostgreSQL
POSTGRES_DB_HOST = "localhost"
POSTGRES_DB_PORT = 5432
POSTGRES_DB_NAME = "media_crawler"
```

### 连接验证

启动爬虫或 API 服务时会自动验证数据库连接。如果验证失败，命令行模式会终止运行，API 模式会继续启动但数据存储不可用。

也可以手动检查：
```bash
# API 端点
curl http://localhost:8080/api/db/check
```

### 迁移

数据库迁移脚本在 `database/migrations/`，包括：
- `create_webui_tables.sql` - WebUI 表结构
- `add_wechat_tables.sql` - 微信相关表
- `add_incremental_metadata.sql` - 增量爬取元数据表

---

## 5. 测试

```bash
# 运行所有测试
uv run pytest

# 运行指定测试文件
uv run pytest test/test_proxy_ip_pool.py

# 详细输出
uv run pytest -v
```

---

## 6. 调试技巧

### 登录问题

- 设置 `HEADLESS = False` 查看浏览器窗口
- 检查 `browser_data/` 下的缓存登录态
- 小红书：可能需要手动通过滑块验证
- 抖音：扫码后可能需要手机验证

### 浏览器问题

- **标准模式**：Playwright 启动独立浏览器实例
- **CDP 模式**：连接用户已有的 Chrome/Edge，配置 `ENABLE_CDP_MODE = True`

### WebUI 问题

- 确认后端 API 已启动（默认 8080 端口）
- 前端开发模式默认 5173 端口，会自动代理到 8080
- WebSocket 连接问题：检查后端 `/api/ws/` 路径是否可达

---

## 7. 代码规范

### 文件命名

| 类型 | 规则 | 示例 |
|------|------|------|
| 平台模块 | 使用简写 | xhs, dy, ks, bili, wb |
| 配置文件 | `{platform}_config.py` | `xhs_config.py` |
| 存储实现 | `store/{platform}/_store_impl.py` | `store/xhs/_store_impl.py` |
| 数据模型 | `model/m_{platform}.py` | `model/m_xiaohongshu.py` |

### 提交规范

建议使用语义化提交消息：
- `feat: xxx` - 新功能
- `fix: xxx` - Bug 修复
- `docs: xxx` - 文档更新
- `refactor: xxx` - 重构

---

## 8. 自动化工具（Skills）

项目内置了实用的自动化工具：

```bash
# 健康检查 - 检查系统各组件状态
uv run python skills/health_check.py

# 数据统计报告
uv run python skills/data_statistics.py --platform xhs --days 7

# 版本发布
uv run python skills/version_release.py patch --dry-run

# 交互式菜单
./skills/run.sh
```

详见 `skills/README.md`。
