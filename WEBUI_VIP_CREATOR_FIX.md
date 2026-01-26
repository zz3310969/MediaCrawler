# WebUI VIP创作者ID字段修复

## 🐛 问题描述

### 发现的问题

在使用 WebUI 启动微博 VIP 创作者模式（`creator_vip`）爬取时，发现传入的创作者ID与实际使用的ID不一致：

**传入参数：**
```json
{
  "creator_ids": "7943876498",
  "crawler_type": "creator_vip"
}
```

**实际使用：**
```
[WeiboCrawler] Processing VIP creator: 7948230240  # ❌ 使用了配置文件的默认值
```

### 根本原因

1. **字段映射错误**：
   - `creator` 模式应使用 `creator_ids` 字段
   - `creator_vip` 模式应使用 `vip_creator_ids` 字段
   
2. **前端未区分**：
   - WebUI 前端对两种模式都使用了 `creator_ids` 字段
   - 导致 `vip_creator_ids` 为空，使用了配置文件中的默认值

3. **后端字段定义**：
   ```python
   # api/schemas/crawler.py
   creator_ids: str = ""       # Creator ID list for creator mode
   vip_creator_ids: str = ""   # VIP creator ID list for creator_vip mode
   ```

---

## ✅ 修复方案

### 1. 修改 `App.tsx` - 字段映射逻辑

在提交爬虫启动请求前，根据 `crawler_type` 正确映射字段：

```tsx
const handleStartStop = () => {
  if (isRunning) {
    stopMutation.mutate()
  } else {
    // 根据爬取类型正确映射字段
    const requestData = { ...config }
    
    // creator_vip 模式：creator_ids → vip_creator_ids
    if (config.crawler_type === 'creator_vip') {
      requestData.vip_creator_ids = config.creator_ids
      requestData.creator_ids = ''  // 清空普通创作者ID
    } else if (config.crawler_type === 'creator') {
      // creator 模式：保持 creator_ids
      requestData.vip_creator_ids = ''  // 清空VIP创作者ID
    }
    
    startMutation.mutate(requestData)
  }
}
```

### 2. 优化 `TargetConfig.tsx` - UI 标签

根据爬取类型显示不同的标签和提示：

```tsx
<Label className="text-xs">
  {crawlerType === 'creator_vip' ? 'VIP创作者 ID' : '创作者 ID'}
</Label>
<p className="text-xs text-muted-foreground mb-1">
  {crawlerType === 'creator_vip' 
    ? '输入VIP创作者ID/URL按回车添加，支持批量粘贴（逗号/分号/换行分隔），自动去重'
    : '输入创作者ID/URL按回车添加，支持批量粘贴（逗号/分号/换行分隔），自动去重'
  }
</p>
```

---

## 🔄 重新构建 WebUI

修复后需要重新构建前端：

```bash
cd webui-src
npm install  # 如果还没安装依赖
npm run build
```

构建完成后，新的前端文件会输出到 `api/webui/` 目录。

---

## ✅ 修复验证

### 测试步骤

1. **重新构建 WebUI**
   ```bash
   cd webui-src && npm run build
   ```

2. **启动 API 服务**
   ```bash
   python -m api.main
   ```

3. **访问 WebUI**
   ```
   http://localhost:8080
   ```

4. **配置并启动爬取**
   - 选择平台：`微博 (wb)`
   - 选择类型：`VIP Content Mode (creator_vip)`
   - 输入VIP创作者ID：`7943876498`
   - 点击「开始爬虫」

5. **查看日志验证**
   ```
   [WeiboCrawler] Processing VIP creator: 7943876498  # ✅ 使用了正确的ID
   ```

### 验证清单

- ✅ VIP创作者ID正确传递到后端
- ✅ 日志显示的ID与输入的ID一致
- ✅ UI标签显示"VIP创作者 ID"
- ✅ 不再使用配置文件的默认值

---

## 📊 修复前后对比

### 修复前 ❌

```
用户输入: 7943876498
  ↓
前端: creator_ids = "7943876498"
  ↓
后端接收: {
  "creator_ids": "7943876498",
  "vip_creator_ids": ""  // 为空！
}
  ↓
使用配置文件默认值: WEIBO_VIP_CREATOR_ID_LIST = ["7948230240"]
  ↓
实际爬取: 7948230240 ❌ 错误！
```

### 修复后 ✅

```
用户输入: 7943876498
  ↓
前端: creator_ids = "7943876498"
  ↓
提交前字段映射: {
  "creator_ids": "",
  "vip_creator_ids": "7943876498"  // ✅ 正确映射
}
  ↓
后端接收: vip_creator_ids = "7943876498"
  ↓
实际爬取: 7943876498 ✅ 正确！
```

---

## 🔧 相关文件

### 修改的文件

1. **`webui-src/src/App.tsx`**
   - 添加字段映射逻辑
   - 根据 `crawler_type` 正确设置 `vip_creator_ids` 或 `creator_ids`

2. **`webui-src/src/components/TargetConfig.tsx`**
   - 优化 UI 标签显示
   - `creator_vip` 模式显示"VIP创作者 ID"

### 相关文件（无需修改）

- `api/schemas/crawler.py` - 后端字段定义正确
- `api/services/crawler_manager.py` - 后端处理逻辑正确
- `cmd_arg/arg.py` - 命令行参数定义正确

---

## 📝 最佳实践

### 前端字段使用规范

| 爬取类型 | 前端存储字段 | 后端API字段 | 命令行参数 |
|---------|-------------|------------|----------|
| `search` | `keywords` | `keywords` | `--keywords` |
| `detail` | `specified_ids` | `specified_ids` | `--specified_id` |
| `creator` | `creator_ids` | `creator_ids` | `--creator_id` |
| `creator_vip` | `creator_ids` | **`vip_creator_ids`** | `--vip_creator_id` |

**注意**：`creator_vip` 模式在前端内部仍使用 `creator_ids` 存储，但提交到后端时需要映射为 `vip_creator_ids`。

---

## 🎉 总结

### 修复内容

1. ✅ 修复字段映射逻辑
2. ✅ 优化 UI 标签显示
3. ✅ 确保ID正确传递到后端

### 用户体验提升

- ✅ 输入的ID与实际使用的ID一致
- ✅ UI标签更清晰（VIP创作者 ID）
- ✅ 不再意外使用配置文件默认值

---

**修复完成，请重新构建 WebUI！** 🚀

