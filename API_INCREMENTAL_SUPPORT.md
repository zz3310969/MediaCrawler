# 🌐 API 增量爬取支持完成！

## ✅ 完成情况

增量爬取功能现已完整集成到 **WebUI API** 和**命令行**中！

---

## 🎯 支持的方式

| 使用方式 | 增量支持 | 配置方式 |
|---------|---------|---------|
| **命令行启动** | ✅ | 命令行参数 |
| **WebUI 启动** | ✅ | 图形界面配置 |
| **配置文件** | ✅ | 修改 base_config.py |
| **API 调用** | ✅ | HTTP 请求参数 |

---

## 🚀 使用方法

### 方式1：命令行启动（新增参数）

```bash
# 启用增量爬取
python main.py \
  --platform xhs \
  --type creator \
  --creator_id "creator_id_1,creator_id_2" \
  --enable_incremental true \
  --incremental_threshold 3

# 参数说明：
# --enable_incremental: 是否启用增量 (true/false/yes/no/1/0)
# --incremental_threshold: 早停阈值 (1-10，默认3)
```

**完整示例**：

```bash
# 小红书创作者增量爬取
python main.py \
  --platform xhs \
  --type creator \
  --creator_id "5eb8e1d400000000010075ae,6eb8e1d400000000010075bf" \
  --enable_incremental true \
  --incremental_threshold 3 \
  --save_data_option json \
  --headless false

# 微博创作者增量爬取
python main.py \
  --platform wb \
  --type creator \
  --creator_id "1234567890,9876543210" \
  --enable_incremental true \
  --save_data_option db

# 抖音创作者增量爬取
python main.py \
  --platform dy \
  --type creator \
  --creator_id "https://www.douyin.com/user/MS4wLjA..." \
  --enable_incremental true
```

---

### 方式2：WebUI 启动（图形界面）

#### 步骤1：启动 WebUI

```bash
# 启动 API 服务器
python -m api.main
# 或
uvicorn api.main:app --port 8080
```

访问：`http://localhost:8080`

#### 步骤2：配置增量爬取

1. 选择**爬取类型**为 `Creator Mode` 或 `VIP Content Mode`
2. 在**输出配置**卡片中，找到 **⚡ 增量爬取** 选项
3. ✅ 勾选 **增量爬取**
4. 🔢 设置 **早停阈值**（默认3，推荐3-5）
5. 点击 **▶ 开始爬虫**

#### UI 示例

```
┌─────────────────────────────────────┐
│  输出配置                            │
├─────────────────────────────────────┤
│  保存格式: [JSON File ▼]            │
│                                     │
│  ☑ 评论抓取                         │
│  ☐ 子评论                           │
│  ☐ 无头模式                         │
│                                     │
│  ☑ ⚡ 增量爬取          [高效模式]   │  ← 新增！
│    └─ 早停阈值: [3]                 │  ← 新增！
│        连续 3 条已存在内容就停止爬取   │
└─────────────────────────────────────┘
```

#### 特性说明

- 💡 **智能显示**：只在创作者模式下显示增量选项
- 🎨 **视觉反馈**：启用时显示"高效模式"标签
- 📝 **实时提示**：显示当前阈值的说明文字
- 🔢 **范围限制**：阈值输入框限制在1-10之间

---

### 方式3：API 调用

```bash
# HTTP POST 请求
curl -X POST http://localhost:8080/api/crawler/start \
  -H "Content-Type: application/json" \
  -d '{
    "platform": "xhs",
    "login_type": "qrcode",
    "crawler_type": "creator",
    "creator_ids": "creator_id_1,creator_id_2",
    "save_option": "json",
    "enable_incremental": true,
    "incremental_early_stop": 3
  }'
```

**Python 调用示例**：

```python
import requests

response = requests.post(
    'http://localhost:8080/api/crawler/start',
    json={
        'platform': 'xhs',
        'crawler_type': 'creator',
        'creator_ids': 'creator_id_1,creator_id_2',
        'enable_incremental': True,  # 启用增量
        'incremental_early_stop': 3,  # 早停阈值
        'save_option': 'json',
        'login_type': 'qrcode',
    }
)
print(response.json())
```

---

## 📋 API 更改清单

### 后端更改 (4个文件)

1. **`api/schemas/crawler.py`**
   ```python
   class CrawlerStartRequest(BaseModel):
       # ... 原有字段 ...
       enable_incremental: bool = False  # 新增
       incremental_early_stop: int = 3   # 新增
   ```

2. **`api/services/crawler_manager.py`**
   ```python
   def _build_command(self, config: CrawlerStartRequest):
       # ... 原有逻辑 ...
       # 增量爬取参数
       if config.enable_incremental:
           cmd.extend(["--enable_incremental", "true"])
           cmd.extend(["--incremental_threshold", str(config.incremental_early_stop)])
   ```

3. **`api/main.py`**
   ```python
   @app.get("/api/config/options")
   async def get_config_options():
       return {
           # ... 原有配置 ...
           "incremental_config": {  # 新增
               "description": "增量爬取配置",
               "supports_platforms": ["xhs", "wb", "dy", "bili"],
               "supports_crawler_types": ["creator", "creator_vip"],
               # ...
           }
       }
   ```

4. **`cmd_arg/arg.py`**
   ```python
   def main(
       # ... 原有参数 ...
       enable_incremental: str = str(config.ENABLE_INCREMENTAL_CRAWL),  # 新增
       incremental_threshold: int = config.CREATOR_EARLY_STOP_THRESHOLD,  # 新增
   ):
       config.ENABLE_INCREMENTAL_CRAWL = _to_bool(enable_incremental)
       config.CREATOR_EARLY_STOP_THRESHOLD = incremental_threshold
   ```

### 前端更改 (4个文件)

5. **`webui-src/src/api/crawler.ts`**
   ```typescript
   export interface CrawlerStartRequest {
       // ... 原有字段 ...
       enable_incremental?: boolean  // 新增
       incremental_early_stop?: number  // 新增
   }
   
   export interface IncrementalConfig {  // 新增接口
       description: string
       supports_platforms: Platform[]
       supports_crawler_types: CrawlerType[]
       // ...
   }
   ```

6. **`webui-src/src/hooks/useCrawlerConfig.ts`**
   ```typescript
   const DEFAULT_CONFIG: CrawlerStartRequest = {
       // ... 原有字段 ...
       enable_incremental: false,  // 新增
       incremental_early_stop: 3,  // 新增
   }
   ```

7. **`webui-src/src/components/OutputConfig.tsx`**
   - 添加增量配置的 Props
   - 添加增量爬取的 Checkbox
   - 添加早停阈值的 Input
   - 智能显示逻辑（只在创作者模式显示）

8. **`webui-src/src/App.tsx`**
   - 传递增量配置到 OutputConfig 组件

---

## 🎨 WebUI 界面效果

### 搜索模式（不显示增量选项）

```
┌─────────────────────────────────────┐
│  输出配置                            │
├─────────────────────────────────────┤
│  保存格式: [JSON File ▼]            │
│                                     │
│  ☑ 评论抓取                         │
│  ☐ 子评论                           │
│  ☐ 无头模式                         │
└─────────────────────────────────────┘
```

### 创作者模式（显示增量选项）

```
┌─────────────────────────────────────┐
│  输出配置                            │
├─────────────────────────────────────┤
│  保存格式: [JSON File ▼]            │
│                                     │
│  ☑ 评论抓取                         │
│  ☐ 子评论                           │
│  ☐ 无头模式                         │
│                                     │
│  ☑ ⚡ 增量爬取          [高效模式]   │  ← 新增！
│    ╰─ 早停阈值: [3]                 │  ← 新增！
│       连续 3 条已存在内容就停止爬取   │
└─────────────────────────────────────┘
```

**视觉特点**：
- 🎨 **特殊背景色**：青色高亮，突出重要功能
- ⚡ **闪电图标**：表示高效模式
- 🏷️ **状态标签**：启用时显示"高效模式"
- 📝 **实时说明**：显示阈值的具体含义

---

## 📖 API 文档

### GET `/api/config/options`

返回所有配置选项，包括增量配置信息。

**Response**:
```json
{
  "login_types": [...],
  "crawler_types": [...],
  "save_options": [...],
  "incremental_config": {
    "description": "Incremental crawling (only fetch new content, 10-100x faster)",
    "supports_platforms": ["xhs", "wb", "dy", "bili"],
    "supports_crawler_types": ["creator", "creator_vip"],
    "default_enabled": false,
    "default_threshold": 3,
    "threshold_range": {
      "min": 1,
      "max": 10
    }
  }
}
```

### POST `/api/crawler/start`

启动爬虫，支持增量配置。

**Request Body**:
```json
{
  "platform": "xhs",
  "login_type": "qrcode",
  "crawler_type": "creator",
  "creator_ids": "creator_id_1,creator_id_2",
  "save_option": "json",
  "enable_incremental": true,
  "incremental_early_stop": 3
}
```

**New Fields**:
- `enable_incremental` (boolean): 是否启用增量爬取
- `incremental_early_stop` (integer): 早停阈值 (1-10)

---

## 🔧 命令行参数

### 新增参数

| 参数 | 类型 | 默认值 | 说明 |
|-----|------|-------|------|
| `--enable_incremental` | bool | false | 是否启用增量爬取 |
| `--incremental_threshold` | int | 3 | 早停阈值（连续N条已存在就停止） |

### 示例

```bash
# 启用增量，使用默认阈值3
python main.py --platform xhs --type creator \
  --creator_id "xxx" --enable_incremental true

# 启用增量，自定义阈值5
python main.py --platform xhs --type creator \
  --creator_id "xxx" --enable_incremental true \
  --incremental_threshold 5

# 禁用增量（全量爬取）
python main.py --platform xhs --type creator \
  --creator_id "xxx" --enable_incremental false
```

---

## 📊 测试建议

### 测试1：命令行测试

```bash
# 首次全量爬取
python main.py --platform xhs --type creator \
  --creator_id "your_creator_id" \
  --enable_incremental false

# 第二次增量爬取
python main.py --platform xhs --type creator \
  --creator_id "your_creator_id" \
  --enable_incremental true \
  --incremental_threshold 3
```

**预期效果**：
- 首次：爬取所有历史内容
- 第二次：只爬取新内容，日志显示"🛑 停止爬取"

---

### 测试2：WebUI 测试

1. 启动服务：`python -m api.main`
2. 访问：`http://localhost:8080`
3. 配置：
   - 平台：小红书
   - 类型：Creator Mode
   - 创作者ID：输入测试ID
   - ✅ 勾选 **⚡ 增量爬取**
   - 早停阈值：3
4. 点击：**▶ 开始爬虫**

**预期效果**：
- 输出配置卡片中显示增量选项（带青色高亮）
- 启用时显示"高效模式"标签
- 阈值输入框可调整1-10

---

### 测试3：API 测试

```python
import requests

# 启动增量爬取
response = requests.post(
    'http://localhost:8080/api/crawler/start',
    json={
        'platform': 'xhs',
        'crawler_type': 'creator',
        'creator_ids': 'test_creator_id',
        'enable_incremental': True,
        'incremental_early_stop': 3,
        'save_option': 'json',
        'login_type': 'qrcode',
    }
)

print(response.json())
# 预期返回: {"success": true}
```

---

## 🎨 WebUI 前端实现细节

### 智能显示逻辑

增量配置**仅在创作者模式下显示**：

```typescript
// 判断是否支持增量
const supportsIncremental = 
  incrementalConfig && 
  crawlerType && 
  incrementalConfig.supports_crawler_types.includes(crawlerType)

// 条件渲染
{supportsIncremental && (
  <增量配置UI />
)}
```

**效果**：
- 搜索模式：不显示增量选项
- 详情模式：不显示增量选项
- 创作者模式：✅ 显示增量选项
- VIP模式：✅ 显示增量选项

---

### 样式设计

```tsx
// 特殊的青色高亮样式
className="bg-cyan-500/10 border border-cyan-500/20 
           hover:bg-cyan-500/15"

// 启用状态标签
{enableIncremental && (
  <span className="text-xs text-cyan-400 font-medium">
    高效模式
  </span>
)}

// 早停阈值输入框
<Input
  type="number"
  min={1}
  max={10}
  value={incrementalThreshold}
  // ...
/>
```

---

## 🔄 工作流程

### 完整的增量爬取流程

```
用户在 WebUI 中配置
    ↓
前端发送 POST /api/crawler/start
    ↓
后端接收参数并构建命令
    ↓
cmd: python main.py --enable_incremental true
    ↓
cmd_arg/arg.py 解析参数
    ↓
设置 config.ENABLE_INCREMENTAL_CRAWL = True
    ↓
启动爬虫，使用增量逻辑
    ↓
日志通过 WebSocket 实时推送到前端
    ↓
用户在终端看到增量效果
```

---

## 📱 响应式设计

### 桌面端

```
┌──────────────┬──────────────┬──────────────┐
│  目标配置    │  登录配置    │  输出配置    │
│              │              │  ⚡ 增量爬取  │ ← 显示完整
└──────────────┴──────────────┴──────────────┘
```

### 移动端

```
┌──────────────────────────────────────┐
│  目标配置                            │
├──────────────────────────────────────┤
│  登录配置                            │
├──────────────────────────────────────┤
│  输出配置                            │
│  ⚡ 增量爬取                         │ ← 自动堆叠
└──────────────────────────────────────┘
```

---

## 🐛 故障排查

### 问题1：WebUI 不显示增量选项

**原因**：爬取类型不是 creator 或 creator_vip

**解决**：切换到创作者模式

---

### 问题2：命令行参数不生效

**检查**：
```bash
# 查看帮助信息
python main.py --help

# 应该看到：
# --enable_incremental TEXT    Enable incremental crawling...
# --incremental_threshold INT  Early stop threshold...
```

---

### 问题3：API 返回错误

**检查请求格式**：
```json
{
  "enable_incremental": true,  // ✅ 正确（小写，下划线）
  "enableIncremental": true    // ❌ 错误（驼峰命名）
}
```

---

## 📊 使用场景对比

### 场景1：WebUI 定期监控

**适合**：非技术用户，图形化操作

```
每天打开 WebUI
  ↓
勾选增量爬取
  ↓
点击开始按钮
  ↓
查看终端日志
  ↓
完成（只爬取新内容）
```

---

### 场景2：命令行自动化

**适合**：技术用户，定时任务

```bash
# crontab 定时任务
0 2 * * * cd /path/to/MediaCrawler && \
  python main.py --platform xhs --type creator \
  --creator_id "xxx" --enable_incremental true
```

---

### 场景3：API 集成

**适合**：系统集成，自动化平台

```python
# 每天自动调用
def daily_crawl():
    requests.post('http://localhost:8080/api/crawler/start', json={
        'platform': 'xhs',
        'crawler_type': 'creator',
        'creator_ids': get_creator_ids(),
        'enable_incremental': True,  # 始终启用增量
    })
```

---

## 🎯 总结

### 完成功能

✅ **命令行支持** - 新增 2 个命令行参数  
✅ **API 支持** - 新增 2 个请求字段  
✅ **WebUI 支持** - 图形化配置界面  
✅ **智能显示** - 只在支持的模式下显示  
✅ **类型定义** - 完整的 TypeScript 类型  
✅ **向下兼容** - 不启用时完全不影响  

### 使用方式

| 方式 | 难度 | 适合人群 | 灵活性 |
|-----|------|---------|-------|
| **WebUI** | ⭐ | 所有用户 | ⭐⭐⭐ |
| **命令行** | ⭐⭐ | 技术用户 | ⭐⭐⭐⭐ |
| **API** | ⭐⭐⭐ | 开发者 | ⭐⭐⭐⭐⭐ |

---

## 📖 相关文档

- 🎊 **多平台支持** → `INCREMENTAL_MULTIPLATFORM.md`
- 🌐 **API 支持说明** → `API_INCREMENTAL_SUPPORT.md` (本文档)
- 🚀 **快速开始** → `INCREMENTAL_QUICKSTART.md`
- 📘 **详细指南** → `docs/incremental_crawl_guide.md`

---

**现在，你可以通过任何方式轻松使用增量爬取！** 🎉

