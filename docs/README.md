# MediaCrawler 开发文档

本目录包含 MediaCrawler 项目的完整技术文档，面向新人入门和日常开发参考。

## 文档导航

### 入门必读

| 文档 | 内容 | 适合谁 |
|------|------|--------|
| [项目架构](architecture.md) | 系统架构、模块设计、数据流、类图 | 新人了解全貌 |
| [开发指南](development.md) | 环境搭建、运行调试、WebUI 开发、测试 | 开发者日常参考 |

### 功能模块

| 文档 | 内容 |
|------|------|
| [数据存储](data_storage_guide.md) | CSV/JSON/Excel/SQLite/MySQL/PostgreSQL 存储配置 |
| [增量爬取](incremental_crawl_guide.md) | 增量爬取原理、配置、各模式详解 |
| [代理系统](proxy_enhancement_guide.md) | 代理池、账号绑定、质量评估、故障转移 |
| [反爬增强](ANTI_DETECT_GUIDE.md) | 指纹管理、智能限速、行为模拟、三重绑定 |
| [CDP 模式](CDP模式使用指南.md) | Chrome DevTools Protocol 使用 |
| [Excel 导出](excel_export_guide.md) | 多工作表、专业格式化的 Excel 导出 |
| [微信爬虫](wechat_usage_guide.md) | 微信公众号文章/评论爬取 |

### 平台配置

| 文档 | 内容 |
|------|------|
| [代理使用](代理使用.md) | 代理 IP 使用流程总览 |
| [快代理](快代理使用文档.md) | 快代理配置与使用 |
| [豌豆 HTTP](豌豆HTTP使用文档.md) | 豌豆 HTTP 代理配置 |
| [手机号登录](手机号登录说明.md) | 手机号 + 验证码登录配置 |
| [词云图](词云图使用配置.md) | 评论词云图生成配置 |

### 设计文档

| 文档 | 内容 |
|------|------|
| [多任务系统](MULTI_TASK_DESIGN.md) | WebUI 任务系统的完整设计方案 |
| [多任务详细设计](multi-task/) | 各模块详细接口与实现（11 篇） |
| [常见问题](常见问题.md) | FAQ |

### 社区

| 文档 | 内容 |
|------|------|
| [作者介绍](作者介绍.md) | 联系方式 |
| [微信交流群](微信交流群.md) | 加群方式 |
| [捐赠名单](捐赠名单.md) | 赞赏与捐赠 |

---

> 项目根目录的 `README.md` 面向用户，本目录文档面向开发者。
> `CLAUDE.md` 是 AI 辅助开发的上下文文件，供 Claude Code 使用。
