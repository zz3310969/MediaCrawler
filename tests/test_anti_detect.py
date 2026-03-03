# -*- coding: utf-8 -*-
# @Desc    : 反爬增强系统测试

import asyncio
import pytest
from anti_detect import (
    AntiDetectBindingManager,
    SmartRateLimiter,
    RateLimitConfig,
    HumanBehaviorSimulator,
    AccountHealthManager,
    BrowserFingerprint,
    FingerprintGenerator,
)


class TestFingerprint:
    """测试浏览器指纹"""

    def test_generate_fingerprint(self):
        """测试生成指纹"""
        fp = FingerprintGenerator.generate()
        assert fp.user_agent
        assert fp.viewport_width > 0
        assert fp.viewport_height > 0
        assert fp.fingerprint_id

    def test_generate_with_platform_hint(self):
        """测试带平台提示的生成"""
        fp_mac = FingerprintGenerator.generate(platform_hint="mac")
        assert "Mac" in fp_mac.user_agent
        assert fp_mac.platform == "MacIntel"

        fp_win = FingerprintGenerator.generate(platform_hint="windows")
        assert "Windows" in fp_win.user_agent
        assert fp_win.platform == "Win32"

    def test_to_playwright_args(self):
        """测试转换为 Playwright 参数"""
        fp = FingerprintGenerator.generate()
        args = FingerprintGenerator.to_playwright_args(fp)

        assert args["user_agent"] == fp.user_agent
        assert args["viewport"]["width"] == fp.viewport_width
        assert args["viewport"]["height"] == fp.viewport_height

    def test_to_init_script(self):
        """测试生成注入脚本"""
        fp = FingerprintGenerator.generate()
        script = FingerprintGenerator.to_init_script(fp)

        assert "navigator.webdriver" in script
        assert fp.platform in script
        assert fp.webgl_vendor in script


class TestRateLimiter:
    """测试智能限速器"""

    @pytest.mark.asyncio
    async def test_basic_rate_limit(self):
        """测试基础限速"""
        config = RateLimitConfig(min_interval=0.1, max_interval=0.2)
        limiter = SmartRateLimiter(config)

        start = asyncio.get_event_loop().time()
        await limiter.wait()
        await limiter.wait()
        elapsed = asyncio.get_event_loop().time() - start

        # 应该至少等待 min_interval
        assert elapsed >= 0.1

    @pytest.mark.asyncio
    async def test_hourly_limit(self):
        """测试每小时限制"""
        config = RateLimitConfig(
            min_interval=0.01, max_interval=0.02, hourly_limit=5
        )
        limiter = SmartRateLimiter(config)

        # 发送5次请求
        for _ in range(5):
            await limiter.wait()

        stats = limiter.get_stats()
        assert stats["hourly_requests"] == 5

    def test_get_stats(self):
        """测试获取统计"""
        limiter = SmartRateLimiter()
        stats = limiter.get_stats()

        assert "total_requests" in stats
        assert "hourly_requests" in stats
        assert "daily_requests" in stats


class TestAccountHealth:
    """测试账号健康管理"""

    def test_record_request(self):
        """测试记录请求"""
        manager = AccountHealthManager(storage_path="data/test_health.json")
        manager.record_request("user1", "xhs", success=True)

        health = manager.get_account("user1", "xhs")
        assert health.total_requests == 1
        assert health.success_requests == 1

    def test_record_failed_request(self):
        """测试记录失败请求"""
        manager = AccountHealthManager(storage_path="data/test_health.json")
        manager.record_request("user2", "xhs", success=False)

        health = manager.get_account("user2", "xhs")
        assert health.failed_requests == 1
        assert health.risk_score > 0

    def test_record_captcha(self):
        """测试记录验证码"""
        manager = AccountHealthManager(storage_path="data/test_health.json")
        manager.record_captcha("user3", "xhs")

        health = manager.get_account("user3", "xhs")
        assert health.captcha_count == 1
        assert health.risk_score >= 15

    def test_get_best_account(self):
        """测��获取最佳账号"""
        manager = AccountHealthManager(storage_path="data/test_health.json")

        # 添加多个账号
        manager.record_request("user4", "xhs", success=True)
        manager.record_request("user5", "xhs", success=True)
        manager.record_captcha("user5", "xhs")  # user5 风险更高

        best = manager.get_best_account("xhs")
        assert best.account_id == "user4"  # user4 风险更低

    def test_get_stats(self):
        """测试获取统计"""
        manager = AccountHealthManager(storage_path="data/test_health.json")
        manager.add_account("user6", "xhs")

        stats = manager.get_stats("xhs")
        assert stats["total_accounts"] >= 1


class TestBindingManager:
    """测试绑定管理器"""

    def test_bind_proxy(self):
        """测试绑定代理"""
        manager = AntiDetectBindingManager(storage_path="data/test_bindings.json")
        manager.bind_proxy("user1", "xhs", "proxy_001")

        binding = manager.get_binding("user1", "xhs")
        assert binding.proxy_id == "proxy_001"

    def test_bind_fingerprint(self):
        """测试绑定指纹"""
        manager = AntiDetectBindingManager(storage_path="data/test_bindings.json")
        manager.bind_fingerprint("user2", "xhs", "fp_abc123")

        binding = manager.get_binding("user2", "xhs")
        assert binding.fingerprint_id == "fp_abc123"

    def test_bind_all(self):
        """测试一次性绑定"""
        manager = AntiDetectBindingManager(storage_path="data/test_bindings.json")
        manager.bind_all("user3", "xhs", proxy_id="proxy_002", fingerprint_id="fp_xyz789")

        binding = manager.get_binding("user3", "xhs")
        assert binding.proxy_id == "proxy_002"
        assert binding.fingerprint_id == "fp_xyz789"

    def test_get_or_create_fingerprint(self):
        """测试获取或创建指纹"""
        manager = AntiDetectBindingManager(storage_path="data/test_bindings.json")

        # 第一次调用：创建新指纹
        fp1 = manager.get_or_create_fingerprint("user4", "xhs")
        assert fp1.fingerprint_id

        # 第二次调用：返回相同指纹
        fp2 = manager.get_or_create_fingerprint("user4", "xhs")
        assert fp1.fingerprint_id == fp2.fingerprint_id

    def test_get_complete_binding(self):
        """测试获取完整绑定"""
        manager = AntiDetectBindingManager(storage_path="data/test_bindings.json")

        # 创建绑定
        fp = manager.get_or_create_fingerprint("user5", "xhs")
        manager.bind_proxy("user5", "xhs", "proxy_003")

        # 获取完整绑定
        proxy_id, fingerprint = manager.get_complete_binding("user5", "xhs")
        assert proxy_id == "proxy_003"
        assert fingerprint.fingerprint_id == fp.fingerprint_id

    def test_get_stats(self):
        """测试获取统计"""
        manager = AntiDetectBindingManager(storage_path="data/test_bindings.json")
        manager.bind_all("user6", "xhs", proxy_id="proxy_004", fingerprint_id="fp_test")

        stats = manager.get_stats("xhs")
        assert stats["total_bindings"] >= 1
        assert stats["with_proxy"] >= 1
        assert stats["with_fingerprint"] >= 1


@pytest.mark.asyncio
async def test_integration():
    """集成测试：完整流程"""
    # 初始化
    binding_manager = AntiDetectBindingManager(storage_path="data/test_bindings.json")
    health_manager = AccountHealthManager(storage_path="data/test_health.json")
    rate_limiter = SmartRateLimiter(
        RateLimitConfig(min_interval=0.1, max_interval=0.2)
    )

    account_id = "integration_test_user"
    platform = "xhs"

    # 1. 获取或创建指纹
    fingerprint = binding_manager.get_or_create_fingerprint(account_id, platform)
    assert fingerprint.fingerprint_id

    # 2. 绑定代理
    binding_manager.bind_proxy(account_id, platform, "proxy_integration")

    # 3. 模拟请求
    for i in range(3):
        await rate_limiter.wait()
        success = i < 2  # 前2次成功，第3次失败
        health_manager.record_request(account_id, platform, success)

    # 4. 检查健康状态
    health = health_manager.get_account(account_id, platform)
    assert health.total_requests == 3
    assert health.success_requests == 2
    assert health.failed_requests == 1

    # 5. 检查绑定
    proxy_id, fp = binding_manager.get_complete_binding(account_id, platform)
    assert proxy_id == "proxy_integration"
    assert fp.fingerprint_id == fingerprint.fingerprint_id

    print("✅ 集成测试通过")


if __name__ == "__main__":
    # 运行集成测试
    asyncio.run(test_integration())
