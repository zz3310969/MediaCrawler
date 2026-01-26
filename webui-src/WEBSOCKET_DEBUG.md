# 🔍 WebSocket 连接诊断指南

## ❓ 问题：WebSocket 没有返回数据

让我们一步步排查问题。

## 📋 检查清单

### ✅ 步骤 1：确认后端是否运行

```bash
# 检查后端是否在运行
curl http://localhost:8080/api/health

# 应该返回：{"status":"ok"}
```

如果返回错误，说明后端没有启动。请先启动后端：
```bash
cd /Users/zhengliangtian/Max/pyProjects/MediaCrawler
uv run uvicorn api.main:app --port 8080 --reload
```

---

### ✅ 步骤 2：检查 WebSocket 路径

**前端 WebSocket URL：**
```typescript
// 开发模式
ws://localhost:8080/ws/logs

// 生产模式
ws://{window.location.host}/ws/logs
```

**后端 WebSocket 路由：**
```python
@router.websocket("/ws/logs")
async def websocket_logs(websocket: WebSocket):
    ...
```

路径匹配：✅ `/ws/logs`

---

### ✅ 步骤 3：检查浏览器控制台

打开浏览器开发者工具（F12），查看：

#### Console（控制台）标签
应该看到：
```
WebSocket connected: /ws/logs
```

如果看到错误：
```
WebSocket connection failed
Failed to connect to ws://localhost:8080/ws/logs
```

说明连接失败，检查：
- 后端是否在 8080 端口运行
- 防火墙是否阻止连接

#### Network（网络）标签
1. 切换到 **WS** 过滤器
2. 应该看到 `ws/logs` 连接
3. 状态应该是 **101 Switching Protocols**（绿色）
4. 点击查看 **Messages** 标签，看是否有消息

---

### ✅ 步骤 4：测试后端是否发送日志

后端只有在**爬虫运行时**才会发送日志。测试步骤：

1. **启动爬虫**：
   - 配置好参数
   - 点击"开始爬虫"按钮

2. **观察后端控制台**：
   应该看到：
   ```
   [WS] New connection attempt
   [WS] Connected, active connections: 1
   [WS] Sent X existing logs, entering main loop
   ```

3. **观察前端**：
   - 系统控制台应该开始显示日志
   - ASCII Logo 消失
   - 日志条数增加

---

### ✅ 步骤 5：检查初始日志

后端在 WebSocket 连接时会发送**已有的日志**：

```python
# Send existing logs
for log in crawler_manager.logs:
    await websocket.send_json(log.model_dump())
```

**问题可能是**：
- 如果爬虫还没启动过，`crawler_manager.logs` 是空的
- 所以 WebSocket 连接成功但没有日志显示

**解决方法**：
启动一次爬虫，就会有日志了。

---

## 🐛 常见问题排查

### 问题 1：WebSocket 显示 "未连接"

**检查：**
```bash
# 1. 后端是否运行
lsof -i :8080

# 2. 后端日志是否有 WebSocket 连接信息
# 应该看到：[WS] New connection attempt
```

**解决：**
- 确保后端运行在 8080 端口
- 检查后端控制台是否有错误

---

### 问题 2：WebSocket 连接成功但没有日志

**原因：**
- 爬虫还没有启动
- 后端的 `crawler_manager.logs` 是空的

**解决：**
1. 配置爬虫参数
2. 点击"开始爬虫"
3. 日志会开始出现

**验证：**
```bash
# 查看后端日志
# 应该看到爬虫启动的输出
```

---

### 问题 3：WebSocket 连接后立即断开

**检查后端错误：**
后端控制台可能显示：
```
[WS] Error: ...
[WS] Cleanup done, active connections: 0
```

**常见原因：**
- CORS 配置问题
- WebSocket 协议版本不匹配
- 后端崩溃

---

### 问题 4：只收到初始日志，新日志不显示

**原因：**
广播任务没有正常启动

**检查：**
```python
# 后端应该启动 log_broadcaster 任务
async def log_broadcaster():
    queue = crawler_manager.get_log_queue()
    while True:
        entry = await queue.get()
        await manager.broadcast(entry.model_dump())
```

---

## 🔧 调试步骤

### 1. 增强前端日志

在浏览器控制台查看详细信息：

```typescript
// 前端已有这些日志
console.log('WebSocket connected:', url)
console.log('WebSocket disconnected:', url)
console.error('WebSocket error:', error)
console.error('Failed to parse WebSocket message:', error)
```

### 2. 手动测试 WebSocket

使用浏览器控制台测试：

```javascript
const ws = new WebSocket('ws://localhost:8080/ws/logs')

ws.onopen = () => console.log('Connected!')
ws.onmessage = (event) => console.log('Message:', event.data)
ws.onerror = (error) => console.error('Error:', error)
ws.onclose = () => console.log('Closed')
```

### 3. 检查后端日志

后端应该显示：
```
[WS] New connection attempt
[WS] Connected, active connections: 1
[WS] Sent 0 existing logs, entering main loop
```

---

## 💡 最可能的原因

### 🎯 原因：爬虫还没启动

**现象：**
- WebSocket 显示"已连接"（或 IDLE）
- 但没有任何日志显示
- 只看到 ASCII Logo

**解决：**
1. 配置爬虫参数（平台、类型、关键词等）
2. 点击"▶ 开始爬虫"按钮
3. 爬虫开始运行后会产生日志
4. 日志通过 WebSocket 实时推送到前端

---

## 🧪 完整测试流程

1. **启动后端**：
   ```bash
   uv run uvicorn api.main:app --port 8080 --reload
   ```

2. **启动前端**：
   ```bash
   cd webui-src
   npm run dev
   ```

3. **打开浏览器**：
   - 访问 `http://localhost:5173`
   - 打开开发者工具（F12）

4. **检查连接**：
   - 控制台应该显示：`WebSocket connected: /ws/logs`
   - Network 标签的 WS 过滤器应该显示绿色的连接

5. **启动爬虫**：
   - 选择平台：Bilibili
   - 爬取类型：Search Mode
   - 关键词：`测试`
   - 点击"开始爬虫"

6. **观察日志**：
   - ASCII Logo 消失
   - 开始显示日志
   - 日志条数增加：`0 条记录` → `1 条记录` → `2 条记录`...

---

## 📞 如果还是不行

请提供以下信息：

1. **浏览器控制台的错误信息**
2. **Network 标签的 WebSocket 状态**
3. **后端控制台的输出**
4. **是否点击了"开始爬虫"**

这样我可以帮你进一步诊断问题！

