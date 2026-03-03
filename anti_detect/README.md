# 反爬增强系统

## 简介

反爬增强系统为 MediaCrawler 提供了完整的反检测能力，通过**账号-代理-指纹三重绑定**机制，确保每个账号使用固定的代理IP和浏览器指纹，避免频繁切换导致风控。

## 核心特性

### 🔐 三重绑定机制

```
账号A → 代理IP_1 + 指纹_1 (固定不变)
账号B → 代理IP_2 + 指纹_2 (固定不变)
账号C → 代理IP_3 + 指纹_3 (固定不变)
```

**为什么需要绑定？**

- ❌ 同一账号频繁切换IP → 触发风控
- ❌ 同一账号频繁切换指纹 → 被识别为机器人
- ✅ 固定绑定 → 模拟真实用户，降低风险

### 🎭 浏览器指纹管理

- 随机化 User Agent、分辨率、WebGL 等
- 覆盖 `navigator.webdriver` 等自动化特征
- 持久化存储，重启后保持一致

### ⏱️ 智能限速器

- 模拟人类浏览节奏（随机间隔）
- 偶尔快速连续请求（模拟快速浏览）
- 偶尔长时间停顿（模拟离开、思考）
- 每小时/每天频率限制
- 时段控制（夜间减速）

### 🤖 人类行为模拟

- 非线性滚动（开始快、中间慢、结束快）
- 贝塞尔曲线鼠标移动
- 自然的点击行为（移动-停顿-点击）
- 变速打字
- 随机浏览行为

### 💚 账号健康管理

- 自动跟踪请求成功率
- 记录验证码遇到次数
- 风险评分（0-100）
- 自动冷却高风险账号

## 快速开始

### 1. 基础使用

```python
from anti_detect import AntiDetectBindingManager
from anti_detect.fingerprint import FingerprintGenerator
from playwright.async_api import async_playwright

# 初始化绑定管理器
binding_manager = AntiDetectBindingManager()

# 为账号获取或创建指纹（自动绑定）
account_id = "user123"
platform = "xhs"
fingerprint = binding_manager.get_or_create_fingerprint(account_id, platform)

# 启动浏览器并应用指纹
async with async_playwright() as p:
    browser = await p.chromium.launch()
    context = await browser.new_context(
        user_agent=fingerprint.user_agent,
        viewport={"width": fingerprint.viewport_width, "height": fingerprint.viewport_height},
        device_scale_factor=fingerprint.pixel_ratio,
    )

    # 注入指纹脚本
    await context.add_init_script(FingerprintGenerator.to_init_script(fingerprint))

    page = await context.new_page()
    await page.goto("https://www.xiaohongshu.com")
```

### 2. 完整示例

查看 `examples/anti_detect_xhs_crawler.py` 获取完整的集成示例。

```bash
# 运行示例
uv run python examples/anti_detect_xhs_crawler.py
```

### 3. 运行测试

```bash
# 运行所有测试
uv run pytest tests/test_anti_detect.py -v

# 运行集成测试
uv run python tests/test_anti_detect.py
```

## 模块说明

### 1. 浏览器指纹 (`fingerprint.py`)

```python
from anti_detect import FingerprintGenerator

# 生成随机指纹
fingerprint = FingerprintGenerator.generate()

# 生成指定平台的指纹
fingerprint = FingerprintGenerator.generate(platform_hint="mac")

# 转换为 Playwright 参数
args = FingerprintGenerator.to_playwright_args(fingerprint)

# 生成注入脚本
script = FingerprintGenerator.to_init_script(fingerprint)
```

### 2. 智能限速器 (`rate_limiter.py`)

```python
from anti_detect import SmartRateLimiter, RateLimitConfig

# 创建限速器
config = RateLimitConfig(
    min_interval=3.0,
    max_interval=10.0,
    hourly_limit=150,
    daily_limit=1500,
)
limiter = SmartRateLimiter(config)

# 等待限速
await limiter.wait()

# 获取统计
stats = limiter.get_stats()
```

### 3. 人类行为模拟 (`human_behavior.py`)

```python
from anti_detect import HumanBehaviorSimulator

# 人类滚动
await HumanBehaviorSimulator.human_scroll(page, direction="down", distance=500)

# 人类点击
await HumanBehaviorSimulator.human_click(page, "button.submit")

# 人类打字
await HumanBehaviorSimulator.human_type(page, "input.search", "美食")

# 随机浏览
await HumanBehaviorSimulator.random_browse(page, duration=5.0)
```

### 4. 账号健康管理 (`account_health.py`)

```python
from anti_detect import AccountHealthManager

manager = AccountHealthManager()

# 记录请求
manager.record_request("user123", "xhs", success=True)

# 记录验证码
manager.record_captcha("user123", "xhs")

# 获取最佳账号
best_account = manager.get_best_account("xhs")

# 获取统计
stats = manager.get_stats("xhs")
```

### 5. 绑定管理器 (`binding_manager.py`)

```python
from anti_detect import AntiDetectBindingManager

manager = AntiDetectBindingManager()

# 绑定代理
manager.bind_proxy("user123", "xhs", "proxy_001")

# 绑定指纹
manager.bind_fingerprint("user123", "xhs", "fp_abc123")

# 一次性绑定
manager.bind_all("user123", "xhs", proxy_id="proxy_001", fingerprint_id="fp_abc123")

# 获取或创建指纹（推荐）
fingerprint = manager.get_or_create_fingerprint("user123", "xhs")

# 获取完整绑定
proxy_id, fingerprint = manager.get_complete_binding("user123", "xhs")
```

## 集成到现有爬虫

### 方案1：修改 base_crawler.py

在 `AbstractCrawler` 中添加反爬增强支持：

```python
from anti_detect import AntiDetectBindingManager, SmartRateLimiter, AccountHealthManager
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
        fingerprint = self.binding_manager.get_or_create_fingerprint(
            account_id, self.platform
        )

        context = await self.browser.new_context(
            user_agent=fingerprint.user_agent,
            viewport={"width": fingerprint.viewport_width, "height": fingerprint.viewport_height},
            device_scale_factor=fingerprint.pixel_ratio,
        )

        await context.add_init_script(FingerprintGenerator.to_init_script(fingerprint))
        return context
```

### 方案2：独立使用

参考 `examples/anti_detect_xhs_crawler.py` 创建独立的爬虫类。

## 配置说明

### 平台配置

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
    min_interval=5.0,
    max_interval=15.0,
    hourly_limit=100,
    daily_limit=1000,
)
```

## 数据存储

所有数据默认存储在 `data/` 目录：

```
data/
├── fingerprints.json           # 浏览器指纹
├── account_health.json         # 账号健康数据
└── anti_detect_bindings.json   # 绑定关系
```

## 最佳实践

### ✅ 推荐做法

1. **使用绑定管理器**

```python
# ✅ 推荐：自动绑定
fingerprint = binding_manager.get_or_create_fingerprint(account_id, platform)

# ❌ 不推荐：每次随机生成
fingerprint = FingerprintGenerator.generate()
```

2. **使用智能限速**

```python
# ✅ 推荐：智能限速
await rate_limiter.wait()

# ❌ 不推荐：固定延迟
await asyncio.sleep(5)
```

3. **使用人类行为模拟**

```python
# ✅ 推荐：人类点击
await HumanBehaviorSimulator.human_click(page, "button")

# ❌ 不推荐：直接点击
await page.click("button")
```

4. **记录所有请求**

```python
# ✅ 推荐：记录请求结果
health_manager.record_request(account_id, platform, success=True)

# ✅ 推荐：遇到验证码时记录
if "验证码" in page_content:
    health_manager.record_captcha(account_id, platform)
```

### ⚠️ 注意事项

1. **不要频繁切换**：同一账号应始终使用相同的代理和指纹
2. **合理设置限速**：根据平台特点调整限速参数
3. **监控健康状态**：定期检查账号健康统计，及时处理高风险账号
4. **持久化数据**：确保 `data/` 目录有写权限

## 监控和统计

### 账号健康统计

```python
stats = health_manager.get_stats("xhs")
print(f"活跃账号: {stats['active_accounts']}")
print(f"冷却账号: {stats['cooling_accounts']}")
print(f"平均风险: {stats['avg_risk_score']}")
```

### 绑定统计

```python
stats = binding_manager.get_stats("xhs")
print(f"完整绑定: {stats['complete_bindings']}")
```

### 限速统计

```python
stats = rate_limiter.get_stats()
print(f"每小时请求: {stats['hourly_requests']}/{stats['hourly_limit']}")
```

## 故障排查

### 问题1：指纹未生效

**症状**：浏览器仍然被检测为自动化

**解决**：

1. 确保 `add_init_script` 在 `new_page` 之前调用
2. 检查注入脚本是否正确执行
3. 使用 `page.evaluate("navigator.webdriver")` 验证

### 问题2：绑定丢失

**症状**：重启后绑定关系消失

**解决**：

1. 检查 `data/` 目录是否有写权限
2. 查看日志中的保存错误信息

### 问题3：限速不生效

**症状**：请求频率过高

**解决**：

1. 确保每次请求前调用 `await rate_limiter.wait()`
2. 检查配置是否正确加载

## 文档

- [完整使用指南](../docs/ANTI_DETECT_GUIDE.md)
- [API 参考](../docs/ANTI_DETECT_GUIDE.md#api-参考)

## 许可证

本项目遵循 MIT 许可证。
