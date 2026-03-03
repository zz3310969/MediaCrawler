# -*- coding: utf-8 -*-
# @Desc    : 反爬增强集成示例 - 小红书爬虫

import asyncio
from typing import Optional

from playwright.async_api import BrowserContext, Page, async_playwright

from anti_detect import (
    AntiDetectBindingManager,
    SmartRateLimiter,
    RateLimitConfig,
    HumanBehaviorSimulator,
    AccountHealthManager,
)
from anti_detect.fingerprint import FingerprintGenerator
from anti_detect.config import get_platform_config


class AntiDetectXhsCrawler:
    """
    集成反爬增强的小红书爬虫示例

    特点:
    1. 账号-代理-指纹三重绑定
    2. 智能限速
    3. 人类行为模拟
    4. 自动健康管理
    """

    def __init__(self, account_id: str, proxy_url: Optional[str] = None):
        """
        初始化爬虫

        Args:
            account_id: 账号ID
            proxy_url: 代理URL（可选）
        """
        self.account_id = account_id
        self.platform = "xhs"
        self.proxy_url = proxy_url

        # 反爬增强模块
        self.binding_manager = AntiDetectBindingManager()
        self.health_manager = AccountHealthManager()

        # 获取平台配置
        config = get_platform_config(self.platform)
        rate_config = RateLimitConfig(
            min_interval=config.rate_limit_min_interval,
            max_interval=config.rate_limit_max_interval,
            hourly_limit=config.rate_limit_hourly_limit,
            daily_limit=config.rate_limit_daily_limit,
        )
        self.rate_limiter = SmartRateLimiter(rate_config)

        # Playwright 对象
        self.browser = None
        self.context: Optional[BrowserContext] = None
        self.page: Optional[Page] = None

    async def init_browser(self):
        """初始化浏览器（应用指纹）"""
        # 1. 获取或创建指纹
        fingerprint = self.binding_manager.get_or_create_fingerprint(
            self.account_id, self.platform, platform_hint="mac"
        )
        print(f"[AntiDetect] Using fingerprint: {fingerprint.fingerprint_id}")

        # 2. 如果有代理，绑定代理
        if self.proxy_url:
            # 这里简化处理，实际应该从代理管理器获取代理ID
            proxy_id = f"proxy_{hash(self.proxy_url) % 10000}"
            self.binding_manager.bind_proxy(self.account_id, self.platform, proxy_id)
            print(f"[AntiDetect] Bound proxy: {proxy_id}")

        # 3. 启动浏览器
        playwright = await async_playwright().start()
        self.browser = await playwright.chromium.launch(
            headless=False,
            args=[
                "--disable-blink-features=AutomationControlled",
                "--disable-dev-shm-usage",
            ],
        )

        # 4. 创建上下文（应用指纹）
        context_options = {
            "user_agent": fingerprint.user_agent,
            "viewport": {
                "width": fingerprint.viewport_width,
                "height": fingerprint.viewport_height,
            },
            "screen": {
                "width": fingerprint.screen_width,
                "height": fingerprint.screen_height,
            },
            "device_scale_factor": fingerprint.pixel_ratio,
            "locale": fingerprint.language,
            "timezone_id": fingerprint.timezone,
        }

        # 添加代理
        if self.proxy_url:
            context_options["proxy"] = {"server": self.proxy_url}

        self.context = await self.browser.new_context(**context_options)

        # 5. 注入指纹脚本
        await self.context.add_init_script(
            FingerprintGenerator.to_init_script(fingerprint)
        )

        # 6. 创建页面
        self.page = await self.context.new_page()

        print("[AntiDetect] Browser initialized with fingerprint")

    async def close(self):
        """关闭浏览器"""
        if self.page:
            await self.page.close()
        if self.context:
            await self.context.close()
        if self.browser:
            await self.browser.close()

    async def search_notes(self, keyword: str, max_pages: int = 3):
        """
        搜索笔记

        Args:
            keyword: 搜索关键词
            max_pages: 最大页数

        Returns:
            list: 笔记列表
        """
        if not self.page:
            await self.init_browser()

        notes = []

        for page_num in range(1, max_pages + 1):
            try:
                # 限速等待
                print(f"[RateLimit] Waiting before page {page_num}...")
                await self.rate_limiter.wait()

                # 访问搜索页
                url = f"https://www.xiaohongshu.com/search_result?keyword={keyword}&page={page_num}"
                print(f"[Crawler] Visiting: {url}")

                response = await self.page.goto(url, wait_until="networkidle")

                # 记录请求
                success = response.status < 400
                self.health_manager.record_request(
                    self.account_id, self.platform, success
                )

                if not success:
                    print(f"[Crawler] Request failed with status {response.status}")
                    continue

                # 人类行为：等待页面加载
                await HumanBehaviorSimulator.wait_for_page_load(self.page)

                # 人类行为：随机浏览
                print("[HumanBehavior] Random browsing...")
                await HumanBehaviorSimulator.random_browse(self.page, duration=3.0)

                # 人类行为：滚动加载更多
                print("[HumanBehavior] Scrolling...")
                for _ in range(3):
                    await HumanBehaviorSimulator.human_scroll(
                        self.page, direction="down", distance=500
                    )
                    await asyncio.sleep(1)

                # 提取笔记数据（这里简化处理）
                # 实际应该解析页面内容
                page_notes = await self._extract_notes()
                notes.extend(page_notes)

                print(f"[Crawler] Page {page_num}: Found {len(page_notes)} notes")

            except Exception as e:
                print(f"[Crawler] Error on page {page_num}: {e}")
                self.health_manager.record_request(
                    self.account_id, self.platform, success=False
                )

        return notes

    async def _extract_notes(self):
        """提取笔记数据（示例）"""
        # 这里应该实现实际的数据提取逻辑
        # 为了演示，返回模拟数据
        await asyncio.sleep(0.5)
        return [
            {"title": "示例笔记1", "author": "用户A"},
            {"title": "示例笔记2", "author": "用户B"},
        ]

    async def get_health_status(self):
        """获取账号健康状态"""
        health = self.health_manager.get_account(self.account_id, self.platform)
        if health:
            return {
                "account_id": health.account_id,
                "status": health.status,
                "total_requests": health.total_requests,
                "success_requests": health.success_requests,
                "failed_requests": health.failed_requests,
                "risk_score": health.risk_score,
                "is_available": health.is_available(),
            }
        return None

    async def get_rate_limit_stats(self):
        """获取限速统计"""
        return self.rate_limiter.get_stats()


async def main():
    """主函数：演示使用"""
    print("=" * 60)
    print("反爬增强小红书爬虫示例")
    print("=" * 60)

    # 创建爬虫实例
    crawler = AntiDetectXhsCrawler(
        account_id="demo_user_001",
        # proxy_url="http://proxy.example.com:8080"  # 可选代理
    )

    try:
        # 初始化浏览器
        await crawler.init_browser()

        # 搜索笔记
        keywords = ["美食", "旅游"]
        for keyword in keywords:
            print(f"\n{'=' * 60}")
            print(f"搜索关键词: {keyword}")
            print(f"{'=' * 60}")

            notes = await crawler.search_notes(keyword, max_pages=2)
            print(f"\n✅ 共找到 {len(notes)} 条笔记")

        # 查看健康状态
        print(f"\n{'=' * 60}")
        print("账号健康状态")
        print(f"{'=' * 60}")
        health = await crawler.get_health_status()
        if health:
            for key, value in health.items():
                print(f"{key}: {value}")

        # 查看限速统计
        print(f"\n{'=' * 60}")
        print("限速统计")
        print(f"{'=' * 60}")
        rate_stats = await crawler.get_rate_limit_stats()
        for key, value in rate_stats.items():
            print(f"{key}: {value}")

    finally:
        # 关闭浏览器
        await crawler.close()

    print(f"\n{'=' * 60}")
    print("爬取完成")
    print(f"{'=' * 60}")


if __name__ == "__main__":
    asyncio.run(main())
