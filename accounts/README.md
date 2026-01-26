# 多账号配置指南

## 概述

多账号功能允许您配置多个平台账号，爬虫会自动轮换使用这些账号，提高爬取稳定性并降低单个账号被限流的风险。

## 快速开始

### 1. 启用多账号模式

在 `config/base_config.py` 中设置：

```python
ENABLE_MULTI_ACCOUNT = True
```

### 2. 创建账号配置文件

将示例文件复制并重命名：

```bash
cp accounts/xhs_accounts.example.json accounts/xhs_accounts.json
```

然后编辑 `accounts/xhs_accounts.json`，填入您的账号信息。

### 3. 配置账号信息

每个账号需要以下信息之一：
- **Cookie方式**：填写 `cookies` 字段
- **浏览器数据目录方式**：填写 `browser_data_dir` 字段

## 配置文件格式

```json
{
  "platform": "xhs",
  "accounts": [
    {
      "account_id": "唯一标识",
      "platform": "平台名称",
      "name": "账号备注名",
      "cookies": "Cookie字符串",
      "browser_data_dir": "浏览器数据目录路径",
      "proxy_ip": "代理IP（可选）",
      "proxy_port": 8080,
      "proxy_user": "代理用户名（可选）",
      "proxy_password": "代理密码（可选）",
      "status": "active"
    }
  ]
}
```

## 账号状态说明

| 状态 | 说明 |
|------|------|
| `active` | 正常可用 |
| `cooling` | 冷却中（被限流后自动设置） |
| `banned` | 被封禁 |
| `invalid` | 登录失效 |
| `unused` | 未使用/未登录 |

## 轮换策略

在 `config/base_config.py` 中配置 `ACCOUNT_ROTATION_STRATEGY`：

| 策略 | 说明 |
|------|------|
| `round_robin` | 轮询 - 按顺序依次使用每个账号（默认） |
| `random` | 随机 - 随机选择一个可用账号 |
| `least_used` | 最少使用 - 优先使用请求次数最少的账号 |

## 账号绑定代理

每个账号可以绑定专属代理IP，适用于以下场景：
- 不同账号使用不同地区的IP
- 账号与IP一一对应，避免IP混用

配置方式：

```json
{
  "account_id": "xhs_account_001",
  "proxy_ip": "192.168.1.100",
  "proxy_port": 8080,
  "proxy_user": "user",
  "proxy_password": "pass"
}
```

## 获取Cookie的方法

### 方法1：浏览器开发者工具

1. 打开浏览器，登录目标平台
2. 按 F12 打开开发者工具
3. 切换到 "Application" 或 "存储" 标签
4. 在左侧找到 "Cookies"
5. 复制需要的Cookie值

### 方法2：使用浏览器数据目录

1. 首次运行爬虫，使用扫码登录
2. 登录成功后，浏览器数据会保存在 `browser_data/` 目录
3. 将该目录路径填入 `browser_data_dir` 字段

## 各平台关键Cookie

| 平台 | 关键Cookie |
|------|------------|
| 小红书 (xhs) | `web_session` |
| 微博 (wb) | `WBPSESS`, `SSOLoginState` |
| 抖音 (dy) | `sessionid`, `ttwid` |
| B站 (bili) | `SESSDATA`, `DedeUserID` |
| 快手 (ks) | `passToken`, `userId` |
| 贴吧 (tieba) | `BDUSS`, `STOKEN` |
| 知乎 (zhihu) | `z_c0` |

## 配置示例

### 小红书多账号

```json
{
  "platform": "xhs",
  "accounts": [
    {
      "account_id": "xhs_main",
      "name": "主账号",
      "cookies": "web_session=xxx",
      "status": "active"
    },
    {
      "account_id": "xhs_backup",
      "name": "备用账号",
      "cookies": "web_session=yyy",
      "status": "active"
    }
  ]
}
```

### 带代理的账号

```json
{
  "platform": "wb",
  "accounts": [
    {
      "account_id": "wb_account_1",
      "name": "微博账号1-北京IP",
      "cookies": "WBPSESS=xxx",
      "proxy_ip": "1.2.3.4",
      "proxy_port": 8080,
      "status": "active"
    },
    {
      "account_id": "wb_account_2",
      "name": "微博账号2-上海IP",
      "cookies": "WBPSESS=yyy",
      "proxy_ip": "5.6.7.8",
      "proxy_port": 8080,
      "status": "active"
    }
  ]
}
```

## 相关配置项

```python
# config/base_config.py

# 是否启用多账号模式
ENABLE_MULTI_ACCOUNT = True

# 账号配置文件目录
ACCOUNTS_DIR = "./accounts"

# 账号轮换策略
ACCOUNT_ROTATION_STRATEGY = "round_robin"

# 账号冷却时间（分钟）
ACCOUNT_COOLING_MINUTES = 30

# 是否在账号被限流时自动切换
AUTO_SWITCH_ON_RATE_LIMIT = True

# 单个账号连续失败多少次后标记为冷却
MAX_CONSECUTIVE_FAILURES = 3

# 是否为每个账号绑定固定代理
ENABLE_ACCOUNT_PROXY_BINDING = False
```

## 注意事项

1. **Cookie有效期**：Cookie可能会过期，需要定期更新
2. **账号安全**：请勿将账号配置文件提交到公开仓库
3. **合理使用**：请遵守平台使用条款，合理控制爬取频率
4. **代理质量**：使用高质量代理可以提高爬取成功率

## 故障排除

### 账号一直处于冷却状态

检查 `cooling_until` 字段，可以手动将 `status` 改为 `active` 并清空 `cooling_until`。

### 账号被标记为无效

重新获取Cookie并更新配置文件，然后将 `status` 改为 `active`。

### 没有可用账号

检查所有账号的状态，确保至少有一个账号的 `status` 为 `active`。

