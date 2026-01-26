# 🧪 WebUI 增量爬取功能测试指南

## 📋 测试清单

### ✅ 前端已编译（刚刚完成）

```
编译时间: 2026-01-26 14:44
文件:
  - api/webui/assets/index-Cbtup_X1.js (280KB)
  - api/webui/assets/index-DE8MlwEc.css (32KB)
```

---

## 🔍 排查步骤

### 步骤1：确认 API 服务正在运行

```bash
# 检查进程
ps aux | grep "api.main"

# 如果没有运行，启动它
python -m api.main
```

**预期输出**：
```
INFO:     Started server process [xxxxx]
INFO:     Waiting for application startup.
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8080
```

---

### 步骤2：测试 API 接口

打开新终端，测试配置接口：

```bash
curl http://localhost:8080/api/config/options
```

**预期返回（应该包含）**：
```json
{
  "incremental_config": {
    "description": "Incremental crawling (only fetch new content, 10-100x faster)",
    "supports_platforms": ["xhs", "wb", "dy", "bili"],
    "supports_crawler_types": ["creator", "creator_vip"],
    "default_enabled": false,
    "default_threshold": 3,
    "threshold_range": {"min": 1, "max": 10}
  }
}
```

**如果没有这个字段**：
- 说明 API 代码没生效
- 需要重启 API 服务

---

### 步骤3：清除浏览器缓存

**方法1：硬刷新**
- Chrome/Edge: `Ctrl + Shift + R` (Windows) 或 `Cmd + Shift + R` (Mac)
- Firefox: `Ctrl + F5` (Windows) 或 `Cmd + Shift + R` (Mac)

**方法2：清除缓存**
1. 打开开发者工具 (F12)
2. 右键点击刷新按钮
3. 选择"清空缓存并硬性重新加载"

**方法3：无痕模式**
- 打开无痕/隐私窗口
- 访问 `http://localhost:8080`

---

### 步骤4：检查浏览器控制台

1. 打开 `http://localhost:8080`
2. 按 `F12` 打开开发者工具
3. 切换到 **Console** 标签
4. 查看是否有错误信息

**常见错误**：
```
Failed to fetch /api/config/options
  → API 服务未启动

TypeError: Cannot read property 'supports_crawler_types'
  → API 返回数据格式不对
```

---

### 步骤5：检查网络请求

在开发者工具中：

1. 切换到 **Network** 标签
2. 刷新页面
3. 找到 `/api/config/options` 请求
4. 点击查看 **Response**

**应该看到**：
```json
{
  "login_types": [...],
  "crawler_types": [...],
  "save_options": [...],
  "incremental_config": {  // ← 这个字段必须存在
    "description": "...",
    "supports_platforms": ["xhs", "wb", "dy", "bili"],
    "supports_crawler_types": ["creator", "creator_vip"]
  }
}
```

---

### 步骤6：验证显示逻辑

在浏览器控制台运行：

```javascript
// 检查配置是否加载
const config = await fetch('/api/config/options').then(r => r.json())
console.log('增量配置:', config.incremental_config)

// 应该输出：
// {
//   description: "...",
//   supports_platforms: ["xhs", "wb", "dy", "bili"],
//   supports_crawler_types: ["creator", "creator_vip"],
//   ...
// }
```

---

## 🎯 完整测试流程

### 测试脚本

```bash
#!/bin/bash
echo "🧪 开始测试 WebUI 增量爬取功能"
echo ""

# 1. 检查 API 服务
echo "1️⃣ 检查 API 服务..."
if curl -s http://localhost:8080/api/health > /dev/null 2>&1; then
    echo "   ✅ API 服务运行中"
else
    echo "   ❌ API 服务未运行"
    echo "   💡 请运行: python -m api.main"
    exit 1
fi

# 2. 检查配置接口
echo ""
echo "2️⃣ 检查配置接口..."
response=$(curl -s http://localhost:8080/api/config/options)
if echo "$response" | grep -q "incremental_config"; then
    echo "   ✅ 增量配置已返回"
else
    echo "   ❌ 增量配置缺失"
    echo "   💡 请重启 API 服务"
    exit 1
fi

# 3. 检查前端文件
echo ""
echo "3️⃣ 检查前端编译..."
if [ -f "api/webui/assets/index-Cbtup_X1.js" ]; then
    echo "   ✅ 前端已编译"
    ls -lh api/webui/assets/index-Cbtup_X1.js
else
    echo "   ❌ 前端未编译"
    echo "   💡 请运行: cd webui-src && npm run build"
    exit 1
fi

echo ""
echo "✅ 所有检查通过！"
echo ""
echo "📝 下一步："
echo "   1. 打开浏览器: http://localhost:8080"
echo "   2. 选择爬取类型: Creator Mode"
echo "   3. 查看输出配置卡片"
echo "   4. 应该能看到 ⚡ 增量爬取 选项"
echo ""
```

保存为 `test_webui_incremental.sh`，然后运行：

```bash
chmod +x test_webui_incremental.sh
./test_webui_incremental.sh
```

---

## 🐛 可能的问题

### 问题1：看不到增量选项

**原因**：爬取类型不是 Creator Mode

**解决**：
1. 在**目标配置**卡片中
2. 找到**爬取类型**下拉框
3. 选择 `Creator Mode` 或 `VIP Content Mode (Weibo)`

---

### 问题2：API 返回没有 incremental_config

**原因**：API 服务没有重启

**解决**：
```bash
# 停止旧的 API 服务（Ctrl+C）
# 重新启动
python -m api.main
```

---

### 问题3：浏览器显示旧版本

**原因**：浏览器缓存

**解决**：
1. 硬刷新：`Cmd + Shift + R` (Mac) 或 `Ctrl + Shift + R` (Windows)
2. 或使用无痕模式

---

### 问题4：前端编译失败

**原因**：依赖未安装

**解决**：
```bash
cd webui-src
npm install
npm run build
```

---

## 📸 预期效果截图说明

### 当你选择 Creator Mode 后

**输出配置卡片应该显示**：

```
┌─────────────────────────────────────┐
│  📤 输出配置                         │
│     保存格式及后处理选项              │
├─────────────────────────────────────┤
│  保存格式                            │
│  [JSON File          ▼]            │
│                                     │
│  爬取选项                            │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓│
│  ┃ ☑ 评论抓取                      ┃│
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛│
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓│
│  ┃ ☐ 子评论                        ┃│
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛│
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓│
│  ┃ ☐ 无头模式                      ┃│
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛│
│                                     │
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓│ ← 青色背景
│  ┃ ☐ ⚡ 增量爬取                   ┃│
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛│
└─────────────────────────────────────┘
```

**勾选后**：

```
│  ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓│
│  ┃ ☑ ⚡ 增量爬取      [高效模式]   ┃│ ← 显示标签
│  ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛│
│    ┏━━━━━━━━━━━━━━━━━━━━━━━━━━━━┓│ ← 展开阈值设置
│    ┃ 早停阈值                     ┃│
│    ┃ [ 3 ]                        ┃│
│    ┃ 连续 3 条已存在内容就停止爬取 ┃│
│    ┗━━━━━━━━━━━━━━━━━━━━━━━━━━━━┛│
```

---

## 🔧 手动验证步骤

### 1. 重启 API 服务

```bash
# 如果 API 正在运行，按 Ctrl+C 停止
# 然后重新启动
cd /Users/zhengliangtian/Max/pyProjects/MediaCrawler
python -m api.main
```

### 2. 打开浏览器

访问：`http://localhost:8080`

### 3. 操作步骤

1. **目标配置** → 选择 `Creator Mode` ✅
2. **输出配置** → 应该看到 `⚡ 增量爬取` ✅
3. 勾选增量爬取 → 应该显示 `[高效模式]` 标签 ✅
4. 应该展开 `早停阈值` 输入框 ✅

### 4. 开发者工具检查

按 `F12`，在 Console 中运行：

```javascript
// 检查 API 返回
fetch('/api/config/options')
  .then(r => r.json())
  .then(data => {
    console.log('✅ 增量配置:', data.incremental_config)
    console.log('✅ 支持平台:', data.incremental_config?.supports_platforms)
    console.log('✅ 支持类型:', data.incremental_config?.supports_crawler_types)
  })
```

**应该看到**：
```
✅ 增量配置: {description: "...", supports_platforms: Array(4), ...}
✅ 支持平台: ["xhs", "wb", "dy", "bili"]
✅ 支持类型: ["creator", "creator_vip"]
```

---

## 🎯 如果还是看不到

### 可能原因1：浏览器缓存

**解决**：
```bash
# 完全清除缓存
1. 打开 http://localhost:8080
2. F12 打开开发者工具
3. 右键点击刷新按钮
4. 选择"清空缓存并硬性重新加载"
```

### 可能原因2：API 服务是旧进程

**解决**：
```bash
# 完全停止所有 API 进程
pkill -f "api.main"

# 重新启动
python -m api.main
```

### 可能原因3：端口冲突

**解决**：
```bash
# 检查端口占用
lsof -i :8080

# 如果有其他进程，杀掉它
kill -9 <PID>

# 或使用其他端口
uvicorn api.main:app --port 8888
# 然后访问 http://localhost:8888
```

---

## 📝 调试信息收集

如果还是不行，请收集以下信息：

### 1. API 返回数据

```bash
curl http://localhost:8080/api/config/options | python -m json.tool > api_response.json
cat api_response.json
```

### 2. 浏览器控制台截图

1. F12 打开开发者工具
2. Console 标签
3. 截图所有错误信息

### 3. Network 请求详情

1. F12 → Network 标签
2. 刷新页面
3. 找到 `/api/config/options` 请求
4. 查看 Response 内容

---

## 🚀 快速测试命令

创建这个测试脚本：

```bash
#!/bin/bash
# test_webui_quick.sh

echo "🧪 WebUI 增量爬取快速测试"
echo ""

# 测试 API
echo "📡 测试 API 接口..."
response=$(curl -s http://localhost:8080/api/config/options)

if echo "$response" | grep -q "incremental_config"; then
    echo "✅ API 返回正确"
    echo ""
    echo "增量配置详情:"
    echo "$response" | python -c "import sys, json; data=json.load(sys.stdin); print(json.dumps(data.get('incremental_config'), indent=2))"
else
    echo "❌ API 返回缺少 incremental_config"
    echo ""
    echo "完整返回:"
    echo "$response" | python -m json.tool
    exit 1
fi

echo ""
echo "✅ 测试通过！"
echo ""
echo "📝 下一步:"
echo "1. 打开浏览器: http://localhost:8080"
echo "2. 硬刷新: Cmd+Shift+R (Mac) 或 Ctrl+Shift+R (Windows)"
echo "3. 选择 Creator Mode"
echo "4. 查看输出配置卡片"
```

运行：
```bash
chmod +x test_webui_quick.sh
./test_webui_quick.sh
```

---

## 💡 确认清单

在浏览器中，按照这个清单检查：

- [ ] API 服务正在运行（http://localhost:8080/api/health 返回 ok）
- [ ] 选择了 Creator Mode 或 VIP Content Mode
- [ ] 输出配置卡片中有 4 个选项（评论、子评论、无头、**增量**）
- [ ] 增量爬取选项有**青色背景**
- [ ] 增量爬取前面有 **⚡ 图标**
- [ ] 勾选后右侧显示 **[高效模式]** 标签
- [ ] 勾选后下方展开 **早停阈值** 输入框

---

## 🎬 视频演示步骤

如果你想录制演示，按这个流程：

1. **启动服务** → `python -m api.main`
2. **打开浏览器** → `http://localhost:8080`
3. **选择平台** → 小红书
4. **选择类型** → Creator Mode ← **关键步骤**
5. **输入创作者ID** → 任意测试ID
6. **查看输出配置** → 应该看到增量选项
7. **勾选增量** → 看到高效模式标签
8. **查看阈值** → 看到输入框和说明

---

## 🔍 详细排查

如果按照上述步骤还是看不到，请运行：

```bash
# 完整的诊断脚本
cd /Users/zhengliangtian/Max/pyProjects/MediaCrawler

echo "=== 1. 检查前端文件 ==="
ls -lh api/webui/assets/

echo ""
echo "=== 2. 检查 API 代码 ==="
grep -n "incremental_config" api/main.py

echo ""
echo "=== 3. 测试 API 接口 ==="
curl -s http://localhost:8080/api/config/options | python -m json.tool | grep -A 10 "incremental"

echo ""
echo "=== 4. 检查前端源码 ==="
grep -n "supportsIncremental" webui-src/src/components/OutputConfig.tsx
```

把输出结果发给我，我帮你分析问题！

---

## 📞 需要帮助？

如果还是不行，请提供：

1. API 接口返回的完整 JSON
2. 浏览器控制台的错误信息
3. 当前选择的爬取类型
4. 浏览器类型和版本

我会帮你快速定位问题！🔧

---

**前端代码已经写好并编译完成，理论上应该能看到效果！** ✨


