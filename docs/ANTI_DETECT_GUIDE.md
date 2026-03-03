# 反爬增强系统使用指南

## 概述

反爬增强系统提供了完整的反检测能力，包括：

1. **浏览器指纹管理**：随机化浏览器指纹，避免被识别
2. **智能限速器**：模拟人类浏览节奏，避免频率过高
3. **人类行为模拟**：模拟真实用户操作（滚动、点击、打字）
4. **账号健康管理**：跟踪账号状态，自动冷却高风险账号
5. **三重绑定**：账���-代理-指纹绑定，避免频繁切换

## 核心特性

### 1. 账号-代理-指纹三重绑定

**为什么需要绑定？**

- 同一账号频繁切换IP会被风控
- 同一账号频繁切换浏览器指纹会被识别为机器人
- 绑定后，每个账号始终使用固定的代理和指纹，降低风险

**绑定关系：**

```
账号A → 代理IP_1 + 指纹_1
账号B → 代理IP_2 + 指纹_2
账号C → 代理IP_3 + 指纹_3
```

### 2. 自动健康管理

系统会自动跟踪每个账号的：

- 请求成功率
- 验证码遇到次数
- 每日请求量
- 风险评分（0-100）

当风险评分过高时，自动进入冷却状态，避免被封禁。

## 快速开始

### 基础使用

```python
from anti_detect import AntiDetectBindingManager
from playwright.async_api import async_playwright

# 初始化绑定管理器
binding_manager = AntiDetectBindingManager()

# 为账号获取或创建指纹
account_id = "user123"
platform = "xhs"
fingerprint = binding_manager.get_or_create_fingerprint(account_id, platform)

# 启动浏览器并应用指纹
async with async_playwright() as p:
    browser = await p.chromium.launch(headless=False)

    # 使用指纹创建上下文
    context = await browser.new_context(
        user_agent=fingerprint.user_agent,
        viewport={
            "width": fingerprint.viewport_width,
            "height": fingerprint.viewport_height,
        },
        screen={
            "width": fingerprint.screen_width,
            "height": fingerprint.screen_height,
        },
        device_scale_factor=fingerprint.pixel_ratio,
        locale=fingerprint.language,
        timezone_id=fingerprint.timezone,
    )

    # 注入指纹脚本
    from anti_detect.fingerprint import FingerprintGenerator
    await context.add_init_script(FingerprintGenerator.to_init_script(fingerprint))

    page = await context.new_page()
    await page.goto("https://www.xiaohongshu.com")
```

### 完整示例：带限速和行为模拟

```python
import asyncio
from anti_detect import (
    AntiDetectBindingManager,
    SmartRateLimiter,
    RateLimitConfig,
    HumanBehaviorSimulator,
    AccountHealthManager,
)
from anti_detect.fingerprint import FingerprintGenerator
from playwright.async_api import async_playwright


async def crawl_with_anti_detect():
    """完整的反爬增强爬虫示例"""

    # 1. 初始化各模块
    binding_manager = AntiDetectBindingManager()
    health_manager = AccountHealthManager()

    # 2. 配置限速��
    rate_config = RateLimitConfig(
        min_interval=3.0,
        max_interval=10.0,
        hourly_limit=150,
        daily_limit=1500,
    )
    rate_limiter = SmartRateLimiter(rate_config)

    # 3. 账号信息
    account_id = "user123"
    platform = "xhs"

    # 4. 获取或创建指纹
    fingerprint = binding_manager.get_or_create_fingerprint(
        account_id, platform, platform_hint="mac"
    )

    # 5. 启动浏览器
    async with async_playwright() as p:
        browser = await p.chromium.launch(headless=False)

        # 应用指纹
        context = await browser.new_context(
            user_agent=fingerprint.user_agent,
            viewport={
                "width": fingerprint.viewport_width,
                "height": fingerprint.viewport_height,
            },
            screen={
                "width": fingerprint.screen_width,
                "height": fingerprint.screen_height,
            },
            device_scale_factor=fingerprint.pixel_ratio,
            locale=fingerprint.language,
            timezone_id=fingerprint.timezone,
        )

        # 注入指纹脚本
        await context.add_init_script(FingerprintGenerator.to_init_script(fingerprint))

        page = await context.new_page()

        # 6. 开始爬取
        keywords = ["美食", "旅游", "摄影"]

        for keyword in keywords:
            # 限速等待
            await rate_limiter.wait()

            # 访问搜索页
            await page.goto(f"https://www.xiaohongshu.com/search_result?keyword={keyword}")

            # 人类行为模拟：随机浏览
            await HumanBehaviorSimulator.random_browse(page, duration=5.0)

            # 人类行为模拟：滚动
            await HumanBehaviorSimulator.human_scroll(page, direction="down", distance=500)

            # 提取数据...
            # ...

            # 记录请求成功
            health_manager.record_request(account_id, platform, success=True)

        # 7. 查看统计
        stats = health_manager.get_stats(platform)
        print(f"账号健康统计: {stats}")

        await browser.close()


if __name__ == "__main__":
    asyncio.run(crawl_with_anti_detect())
```

## 集成到现有爬虫

### 修改 base_crawler.py

在 `AbstractCrawler` 中集成反爬增强：

```python
from anti_detect import (
    AntiDetectBindingManager,
    SmartRateLimiter,
    AccountHealthManager,
)
from anti_detect.fingerprint import FingerprintGenerator


class AbstractCrawler(ABC):
    def __init__(self):
        # 原有初始化...

        # 反爬增强模块
        self.binding_manager = AntiDetectBindingManager()
        self.health_manager = AccountHealthManager()
        self.rate_limiter = SmartRateLimiter()

    async def create_browser_context(self, account_id: str):
        """创建浏览器上下文（应用指纹）"""
        # 获取指纹
        fingerprint = self.binding_manager.get_or_create_fingerprint(
            account_id, self.platform
        )

        # 创建上下文
        context = await self.browser.new_context(
            user_agent=fingerprint.user_agent,
            viewport={
                "width": fingerprint.viewport_width,
                "height": fingerprint.viewport_height,
            },
            screen={
                "width": fingerprint.screen_width,
                "height": fingerprint.screen_height,
            },
            device_scale_factor=fingerprint.pixel_ratio,
            locale=fingerprint.language,
            timezone_id=fingerprint.timezone,
        )

        # 注入指纹脚本
        await context.add_init_script(FingerprintGenerator.to_init_script(fingerprint))

        return context

    async def request_with_rate_limit(self, url: str):
        """带限速的请求"""
        # 等待限速
        await self.rate_limiter.wait()

        # 发送请求
        response = await self.page.goto(url)

        # 记录请求
        success = response.status < 400
        self.health_manager.record_request(
            self.current_account_id, self.platform, success
        )

        return response
```

## 配置说明

### 平台配置

不同平台有不同的推荐配置：

```python
from anti_detect.config import get_platform_config

# 获取小红书推荐配置
config = get_platform_config("xhs")
print(config.rate_limit_hourly_limit)  # 150
```

### 自定义配置

```python
from anti_detect import RateLimitConfig

config = RateLimitConfig(
    min_interval=5.0,        # 最小间隔5秒
    max_interval=15.0,       # 最大间隔15秒
    hourly_limit=100,        # 每小时100次
    daily_limit=1000,        # 每天1000次
    burst_probability=0.05,  # 5%概率快速连续请求
    pause_probability=0.1,   # 10%概率长时间停顿
)
```

## API 参考

### AntiDetectBindingManager

```python
# 初始化
manager = AntiDetectBindingManager()

# 绑定代理
manager.bind_proxy("user123", "xhs", "proxy_001")

# 绑定指纹
manager.bind_fingerprint("user123", "xhs", "fp_abc123")

# 一次性绑定
manager.bind_all("user123", "xhs", proxy_id="proxy_001", fingerprint_id="fp_abc123")

# 获取或创建指纹
fingerprint = manager.get_or_create_fingerprint("user123", "xhs")

# 获取完整绑定
proxy_id, fingerprint = manager.get_complete_binding("user123", "xhs")

# 统计信息
stats = manager.get_stats("xhs")
```

### AccountHealthManager

```python
# 初始化
manager = AccountHealthManager()

# 记录请求
manager.record_request("user123", "xhs", success=True)

# 记录验证码
manager.record_captcha("user123", "xhs")

# 记录封禁
manager.record_ban("user123", "xhs")

# 获取最佳账号
best_account = manager.get_best_account("xhs")

# 统计信息
stats = manager.get_stats("xhs")
```

### SmartRateLimiter

```python
# 初始化
limiter = SmartRateLimiter(config)

# 等待限速
await limiter.wait()

# 获取统计
stats = limiter.get_stats()

# 重置
limiter.reset()
```

### HumanBehaviorSimulator

```python
# 人类滚动
await HumanBehaviorSimulator.human_scroll(page, direction="down", distance=500)

# 人类移动
await HumanBehaviorSimulator.human_move_to(page, x=100, y=200)

# 人类点击
await HumanBehaviorSimulator.human_click(page, "button.submit")

# 人类打字
await HumanBehaviorSimulator.human_type(page, "input.search", "美食")

# 随机浏览
await HumanBehaviorSimulator.random_browse(page, duration=5.0)
```

## 最佳实践

### 1. 账号-代理-指纹绑定

```python
# ✅ 推荐：使用绑定管理器
binding_manager = AntiDetectBindingManager()
fingerprint = binding_manager.get_or_create_fingerprint(account_id, platform)

# ❌ 不推荐：每次随机生成
fingerprint = FingerprintGenerator.generate()  # 会导致频繁切换
```

### 2. 限速策略

```python
# ✅ 推荐：使用智能限速器
await rate_limiter.wait()

# ❌ 不推荐：固定延迟
await asyncio.sleep(5)  # 容易被识别为机器人
```

### 3. 行为模拟

```python
# ✅ 推荐：使用人类行为模拟
await HumanBehaviorSimulator.human_click(page, "button")

# ❌ 不推荐：直接点击
await page.click("button")  # 缺少人类特征
```

### 4. 健康管理

```python
# ✅ 推荐：记录所有请求
health_manager.record_request(account_id, platform, success=True)

# ✅ 推荐：遇到验证码时记录
if "验证码" in page_content:
    health_manager.record_captcha(account_id, platform)

# ✅ 推荐：选择最佳账号
best_account = health_manager.get_best_account(platform)
```

## 故障排查

### 问题1：指纹未生效

**症状**：浏览器仍然被检测为自动化

**解决**：

1. 确保注入脚本在页面加载前执行
2. 检查 `add_init_script` 是否正确调用
3. 使用 `page.evaluate("navigator.webdriver")` 检查是否为 `undefined`

### 问题2：限速不生效

**症状**：请求频率过高

**解决**：

1. 确保每次请求前调用 `await rate_limiter.wait()`
2. 检查配置是否正确加载
3. 查看统计信息 `rate_limiter.get_stats()`

### 问题3：绑定丢失

**症状**：重启后绑定关系消失

**解决**：

1. 检查存储路径是否有写权限
2. 确保 `data/` 目录存在
3. 查看日志中的保存错误信息

## 性能优化

### 1. 批量初始化

```python
# 预先为所有账号创建指纹
for account_id in account_list:
    binding_manager.get_or_create_fingerprint(account_id, platform)
```

### 2. 共享限速器

```python
# 多个爬虫共享同一个限速器
from anti_detect.rate_limiter import PlatformRateLimiter

platform_limiter = PlatformRateLimiter()

# 爬虫1
await platform_limiter.wait("xhs")

# 爬虫2
await platform_limiter.wait("xhs")
```

### 3. 定期清理

```python
# 定期清理过期数据
import os
import time

def cleanup_old_data():
    # 清理30天前的健康数据
    # ...
```

## 监控和告警

### 统计信息

```python
# 账号健康统计
health_stats = health_manager.get_stats("xhs")
print(f"活跃账号: {health_stats['active_accounts']}")
print(f"冷却账号: {health_stats['cooling_accounts']}")
print(f"平均风险: {health_stats['avg_risk_score']}")

# 绑定统计
binding_stats = binding_manager.get_stats("xhs")
print(f"完整绑定: {binding_stats['complete_bindings']}")

# 限速统计
rate_stats = rate_limiter.get_stats()
print(f"每小时请求: {rate_stats['hourly_requests']}/{rate_stats['hourly_limit']}")
```

### 告警示例

```python
def check_health_alerts():
    stats = health_manager.get_stats("xhs")

    # 告警：封禁账号过多
    if stats['banned_accounts'] > 5:
        send_alert(f"警告：{stats['banned_accounts']}个账号被封禁")

    # 告警：平均风险过高
    if stats['avg_risk_score'] > 60:
        send_alert(f"警告：平均风险评分 {stats['avg_risk_score']}")
```

## 总结

反爬增强系统通过以下方式降低被检测风险：

1. **指纹随机化**：每个账号独立的浏览器指纹
2. **固定绑定**：账号-代理-指纹三重绑定，避免频繁切换
3. **智能限速**：模拟人类浏览节奏，避免频率过高
4. **行为模拟**：模拟真实用户操作，增加真实性
5. **健康管理**：自动跟踪账号状态，及时冷却高风险账号

正确使用这些功能，可以大幅降低被封禁的风险。
