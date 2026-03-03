# 反爬增强 WebUI 集成指南

## 概述

反爬增强系统已成功集成到 WebUI 中，用户可以通过图形界面配置和使用账号-代理-指纹三重绑定功能。

## 功能特性

### 1. 任务创建流程集成

在任务创建页面新增了"反爬增强"步骤（第3步），用户可以：

- **启用/禁用反爬增强**：一键开关
- **功能模块配置**：
  - 浏览器指纹：随机化浏览器特征
  - 智能限速：模拟人类浏览节奏
  - 人类行为模拟：自然的滚动、点击、打字
  - 账号健康管理：自动冷却高风险账号
  - 账号-代理-指纹绑定：固定绑定，避免频繁切换

- **限速参数配置**：
  - 最小间隔（秒）：默认 3.0
  - 最大间隔（秒）：默认 10.0
  - 每小时限制：默认 150 次
  - 每天限制：默认 1500 次

### 2. API 端点

新增以下 RESTful API 端点：

```
GET  /api/anti-detect/stats/{platform}
     获取反爬增强统计信息

GET  /api/anti-detect/accounts/{platform}
     获取账号健康列表（支持分页）

GET  /api/anti-detect/bindings/{platform}
     获取绑定关系列表（支持分页）

POST /api/anti-detect/bindings/{platform}/{account_id}/proxy
     绑定代理到账号

DELETE /api/anti-detect/bindings/{platform}/{account_id}
     删除账号绑定

GET  /api/anti-detect/config/default
     获取默认配置
```

## 测试步骤

### 1. 后端测试

运行集成测试脚本：

```bash
uv run python examples/test_anti_detect_webui.py
```

测试内容：
- 创建测试数据（账号、代理、指纹绑定）
- 测试统计 API
- 测试列表 API
- 测试删除 API

### 2. 启动服务

**启动 API 服务器：**

```bash
uv run uvicorn api.main:app --port 8080 --reload
```

**启动前端开发服务器：**

```bash
cd webui-src
npm run dev
```

或使用生产构建：

```bash
cd webui-src
npm run build
# 前端资源会自动构建到 ../api/webui/ 目录
```

### 3. WebUI 测试

1. 访问 http://localhost:5173（开发模式）或 http://localhost:8080（生产模式）
2. 登录系统
3. 进入"创建任务"页面
4. 按照步骤操作：
   - 步骤1：选择平台（如小红书）
   - 步骤2：配置爬取参数
   - **步骤3：配置反爬增强**
     - 启用反爬增强开关
     - 根据需要调整功能模块
     - 配置限速参数
   - 步骤4：配置代理设置
   - 步骤5：确认并执行

### 4. API 测试

使用 curl 或 Postman 测试 API 端点：

```bash
# 获取统计信息
curl -H "X-Session-ID: your-session-id" \
  http://localhost:8080/api/anti-detect/stats/xhs

# 获取账号健康列表
curl -H "X-Session-ID: your-session-id" \
  http://localhost:8080/api/anti-detect/accounts/xhs?page=1&page_size=20

# 获取绑定列表
curl -H "X-Session-ID: your-session-id" \
  http://localhost:8080/api/anti-detect/bindings/xhs?page=1&page_size=20
```

## 技术实现

### 后端

1. **API Schemas** (`api/schemas/anti_detect.py`)
   - `AntiDetectConfig`：反爬增强配置
   - `AntiDetectStats`：统计信息
   - `AccountHealthStatus`：账号健康状态
   - `BindingInfo`：绑定关系信息

2. **API Router** (`api/routers/anti_detect.py`)
   - 实现所有反爬增强相关的 API 端点
   - 支持分页查询
   - 集成 session 验证

3. **Task Schema** (`api/schemas/task.py`)
   - 扩展 `TaskConfig` 支持反爬增强配置
   - 添加 `enable_anti_detect` 和 `anti_detect_config` 字段

4. **Crawler Adapter** (`api/services/crawler_adapter.py`)
   - 在生成临时配置文件时包含反爬增强配置
   - 将 WebUI 配置转换为爬虫配置格式

### 前端

1. **API Client** (`webui-src/src/api/antiDetect.ts`)
   - TypeScript 类型定义
   - API 调用封装

2. **UI Component** (`webui-src/src/components/task-create/Step3AntiDetect.tsx`)
   - 反爬增强配置界面
   - 功能模块开关
   - 限速参数输入

3. **Task Create Page** (`webui-src/src/pages/TaskCreate.tsx`)
   - 集成反爬增强步骤
   - 状态管理
   - 提交时包含反爬增强配置

## 配置说明

### 默认配置

```typescript
{
  enable_fingerprint: true,           // 启用浏览器指纹
  enable_rate_limit: true,            // 启用智能限速
  enable_human_behavior: true,        // 启用人类行为模拟
  enable_account_health: true,        // 启用账号健康管理
  enable_binding: true,               // 启用三重绑定
  rate_limit_min_interval: 3.0,      // 最小间隔（秒）
  rate_limit_max_interval: 10.0,     // 最大间隔（秒）
  rate_limit_hourly_limit: 150,      // 每小时限制
  rate_limit_daily_limit: 1500,      // 每天限制
  account_cooling_threshold: 70.0,   // 账号冷却阈值
  account_warning_threshold: 50.0,   // 账号警告阈值
}
```

### 配置建议

- **保守模式**（低风险）：
  - 最小间隔：5秒
  - 最大间隔：15秒
  - 每小时限制：100次
  - 每天限制：1000次

- **平衡模式**（默认）：
  - 最小间隔：3秒
  - 最大间隔：10秒
  - 每小时限制：150次
  - 每天限制：1500次

- **激进模式**（高效率，高风险）：
  - 最小间隔：1秒
  - 最大间隔：5秒
  - 每小时限制：300次
  - 每天限制：3000次

## 注意事项

1. **三重绑定核心**：确保同一账号始终使用相同的代理IP和浏览器指纹，避免频繁切换导致风控
2. **绑定持久化**：绑定关系会自动保存到 `anti_detect_data/bindings.json`，重启后保持一致
3. **账号健康监控**：系统会自动监控账号健康状态，高风险账号会自动进入冷却期
4. **限速策略**：建议根据平台特性和账号质量调整限速参数

## 下一步开发

可选的增强功能：

1. **账号健康仪表板**：可视化展示账号健康状态
2. **绑定管理页面**：手动管理账号-代理-指纹绑定关系
3. **统计图表**：展示请求成功率、风险趋势等
4. **告警通知**：账号进入警告或冷却状态时发送通知
5. **批量操作**：批量绑定、批量解绑等功能

## 相关文档

- [反爬增强系统设计](./COMMERCIAL_OPTIMIZATION_PLAN.md)
- [API 文档](../../api/README.md)
- [WebUI 开发指南](../../webui-src/README.md)
