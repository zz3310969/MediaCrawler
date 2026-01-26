# 🔧 WebSocket 问题排查指南

## 🐛 问题：启动爬虫后前端没有显示日志

我已经在代码中添加了调试日志，现在可以精确诊断问题。

## 📝 调试步骤

### 1️⃣ 打开浏览器开发者工具

按 **F12** 或右键 → 检查，打开开发者工具

### 2️⃣ 切换到 Console（控制台）标签

### 3️⃣ 清空控制台

点击 🚫 清空按钮，清除旧日志

### 4️⃣ 刷新页面

按 **F5** 刷新页面，观察控制台输出

### 5️⃣ 观察 WebSocket 连接日志

应该看到：
```
WebSocket connected: /ws/logs
WebSocket 已连接
```

如果看到错误：
```
WebSocket error: ...
Failed to create WebSocket: ...
```

说明连接失败，跳到"连接失败排查"部分。

### 6️⃣ 启动爬虫

1. 配置爬虫参数
2. 点击"▶ 开始爬虫"按钮
3. **立即观察控制台**

### 7️⃣ 检查控制台输出

**正常情况**应该看到：
```
WebSocket 原始数据: {id: 1, timestamp: "10:30:25", level: "info", message: "Starting crawler..."}
收到 WebSocket 消息: {id: 1, timestamp: "10:30:25", level: "info", message: "Starting crawler..."}

WebSocket 原始数据: {id: 2, timestamp: "10:30:26", level: "success", message: "爬虫启动成功"}
收到 WebSocket 消息: {id: 2, timestamp: "10:30:26", level: "success", message: "爬虫启动成功"}
```

**异常情况**：

#### 情况 A：只看到 "ping"/"pong"
```
WebSocket 收到: ping
WebSocket 收到: pong
```
说明连接正常，但没有收到日志消息。

#### 情况 B：看到解析错误
```
Failed to parse WebSocket message: ... Raw data: ...
```
说明消息格式有问题。

#### 情况 C：什么都没有
说明 WebSocket 没有收到任何消息。

---

## 🔍 根据控制台输出诊断

### 📊 情况 A：只有 ping/pong，没有日志

**原因**：爬虫可能没有正常启动或后端没有捕获输出

**检查后端控制台**：
```
看后端是否显示：
[WS] Sent X existing logs, entering main loop
Starting crawler: uv run main.py ...
```

**排查**：
1. 后端命令是否正确执行
2. 爬虫进程是否启动
3. 后端是否能读取爬虫输出

---

### 📊 情况 B：解析错误

**原因**：消息格式不匹配

**检查 Raw data**：
看控制台显示的 `Raw data:` 部分是什么内容

**可能的格式问题**：
- 后端发送的不是 JSON
- 消息结构不匹配 LogEntry 类型

---

### 📊 情况 C：没有任何消息

**原因**：WebSocket 连接可能实际上没建立

**检查 Network 标签**：
1. 切换到 **Network** 标签
2. 过滤器选择 **WS**（WebSocket）
3. 查看 `ws/logs` 的状态

**状态码说明**：
- **101 Switching Protocols**（绿色）：连接成功 ✅
- **其他状态码**：连接失败 ❌

**如果是 101 但没消息**：
- 点击 `ws/logs` 连接
- 查看 **Messages** 标签
- 看是否有消息往来

---

## 🧪 手动测试 WebSocket

在浏览器控制台运行：

```javascript
// 手动创建 WebSocket 连接
const ws = new WebSocket('ws://localhost:8080/ws/logs')

ws.onopen = () => {
  console.log('✅ WebSocket 连接成功')
}

ws.onmessage = (event) => {
  console.log('📨 收到消息:', event.data)
  try {
    const data = JSON.parse(event.data)
    console.log('📋 解析后:', data)
  } catch (e) {
    console.log('❌ 无法解析为 JSON')
  }
}

ws.onerror = (error) => {
  console.error('❌ WebSocket 错误:', error)
}

ws.onclose = () => {
  console.log('🔌 WebSocket 关闭')
}
```

然后启动爬虫，观察是否收到消息。

---

## 🔧 可能的解决方案

### 方案 1：Vite 代理配置问题

检查 `vite.config.ts`：

```typescript
server: {
  proxy: {
    '/ws': {
      target: 'ws://localhost:8080',
      ws: true,  // ← 确保这个配置存在
    },
  },
}
```

### 方案 2：后端 CORS 配置

检查 `api/main.py` 的 CORS 配置是否包含 WebSocket：

```python
app.add_middleware(
    CORSMiddleware,
    allow_origins=["http://localhost:5173", ...],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)
```

### 方案 3：WebSocket 路由注册

确认后端注册了 WebSocket 路由：

```python
# api/main.py
app.include_router(websocket_router, prefix="/api")  # ❌ 错误

# 应该是：
app.include_router(websocket_router)  # ✅ 正确（没有 prefix）
```

**检查路径**：
- 前端：`/ws/logs`
- 后端：`/api/ws/logs` 或 `/ws/logs`？

---

## 🎯 立即诊断

### 步骤 1：查看 API 注册

```bash
# 访问后端 API 文档
http://localhost:8080/docs

# 查看 WebSocket 路由路径
# 应该是 /ws/logs 还是 /api/ws/logs？
```

### 步骤 2：测试正确的路径

如果发现是 `/api/ws/logs`，修改前端：

```typescript
// src/components/TerminalLog.tsx
const { isConnected } = useWebSocket({
  url: '/api/ws/logs',  // ← 加上 /api 前缀
  ...
})
```

---

## 📞 请提供以下信息

启动爬虫后，请查看浏览器控制台并告诉我：

1. **WebSocket 连接日志**：
   - 是否看到 "WebSocket connected"？
   - 是否看到 "WebSocket 已连接"？

2. **收到的消息**：
   - 是否看到 "WebSocket 原始数据: ..."？
   - 是否看到 "收到 WebSocket 消息: ..."？
   - 如果有，消息内容是什么？

3. **Network 标签**：
   - WS 过滤器下的 ws/logs 状态码是多少？
   - Messages 标签有没有消息？

4. **后端控制台**：
   - 是否显示 "[WS] Connected, active connections: 1"？
   - 是否显示爬虫启动的日志？

有了这些信息，我可以精确定位问题！

