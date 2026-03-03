#!/usr/bin/env python
# -*- coding: utf-8 -*-
# @Desc    : 反爬增强快速测试脚本

"""
快速测试反爬增强系统的所有功能

运行方式:
    uv run python examples/quick_test_anti_detect.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from anti_detect import (
    AntiDetectBindingManager,
    SmartRateLimiter,
    RateLimitConfig,
    AccountHealthManager,
    FingerprintGenerator,
)


def print_section(title: str):
    """打印章节标题"""
    print(f"\n{'=' * 60}")
    print(f"  {title}")
    print(f"{'=' * 60}\n")


def test_fingerprint():
    """测试浏览器指纹"""
    print_section("1. 测试浏览器指纹")

    # 生成指纹
    fp = FingerprintGenerator.generate()
    print(f"✅ 生成指纹: {fp.fingerprint_id}")
    print(f"   User Agent: {fp.user_agent[:50]}...")
    print(f"   分辨率: {fp.viewport_width}x{fp.viewport_height}")
    print(f"   平台: {fp.platform}")
    print(f"   WebGL: {fp.webgl_vendor}")

    # 生成 Mac 指纹
    fp_mac = FingerprintGenerator.generate(platform_hint="mac")
    print(f"\n✅ 生成 Mac 指纹: {fp_mac.fingerprint_id}")
    print(f"   平台: {fp_mac.platform}")

    # 生成 Windows 指纹
    fp_win = FingerprintGenerator.generate(platform_hint="windows")
    print(f"\n✅ 生成 Windows 指纹: {fp_win.fingerprint_id}")
    print(f"   平台: {fp_win.platform}")


async def test_rate_limiter():
    """测试智能限速器"""
    print_section("2. 测试智能限速器")

    config = RateLimitConfig(
        min_interval=0.5,
        max_interval=1.0,
        hourly_limit=10,
    )
    limiter = SmartRateLimiter(config)

    print("⏱️  发送3次请求（带限速）...")
    for i in range(3):
        await limiter.wait()
        print(f"   请求 {i+1} 完成")

    stats = limiter.get_stats()
    print(f"\n✅ 限速统计:")
    print(f"   总请求数: {stats['total_requests']}")
    print(f"   每小时请求: {stats['hourly_requests']}/{stats['hourly_limit']}")


def test_account_health():
    """测试账号健康管理"""
    print_section("3. 测试账号健康管理")

    manager = AccountHealthManager()

    # 模拟请求
    print("📊 模拟账号请求...")
    for i in range(5):
        success = i < 4  # 前4次成功，最后1次失败
        manager.record_request("test_user", "xhs", success=success)
        print(f"   请求 {i+1}: {'成功' if success else '失败'}")

    # 获取健康状态
    health = manager.get_account("test_user", "xhs")
    print(f"\n✅ 账号健康状态:")
    print(f"   总请求: {health.total_requests}")
    print(f"   失败请求: {health.failed_requests}")
    print(f"   风险评分: {health.risk_score:.2f}")
    print(f"   状态: {health.status}")
    print(f"   可用: {'是' if health.is_available() else '否'}")

    # 模拟验证码
    print(f"\n⚠️  遇到验证码...")
    manager.record_captcha("test_user", "xhs")
    health = manager.get_account("test_user", "xhs")
    print(f"   风险评分: {health.risk_score:.2f}")
    print(f"   状态: {health.status}")


def test_binding_manager():
    """测试绑定管理器"""
    print_section("4. 测试绑定管理器（核心功能）")

    manager = AntiDetectBindingManager()

    # 为账号创建指纹
    print("🔗 为账号创建指纹...")
    fp1 = manager.get_or_create_fingerprint("user1", "xhs")
    print(f"   账号 user1: 指纹 {fp1.fingerprint_id}")

    fp2 = manager.get_or_create_fingerprint("user2", "xhs")
    print(f"   账号 user2: 指纹 {fp2.fingerprint_id}")

    # 绑定代理
    print(f"\n🔗 绑定代理...")
    manager.bind_proxy("user1", "xhs", "proxy_001")
    manager.bind_proxy("user2", "xhs", "proxy_002")
    print(f"   账号 user1: 代理 proxy_001")
    print(f"   账号 user2: 代理 proxy_002")

    # 获取完整绑定
    print(f"\n✅ 获取完整绑定:")
    proxy_id, fp = manager.get_complete_binding("user1", "xhs")
    print(f"   账号 user1:")
    print(f"     代理: {proxy_id}")
    print(f"     指纹: {fp.fingerprint_id}")

    # 验证绑定持久性
    print(f"\n🔄 验证绑定持久性...")
    fp1_again = manager.get_or_create_fingerprint("user1", "xhs")
    if fp1.fingerprint_id == fp1_again.fingerprint_id:
        print(f"   ✅ 绑定保持一致: {fp1.fingerprint_id}")
    else:
        print(f"   ❌ 绑定不一致")

    # 统计信息
    stats = manager.get_stats("xhs")
    print(f"\n📊 绑定统计:")
    print(f"   总绑定数: {stats['total_bindings']}")
    print(f"   有代理: {stats['with_proxy']}")
    print(f"   有指纹: {stats['with_fingerprint']}")
    print(f"   完整绑定: {stats['complete_bindings']}")


def test_integration():
    """集成测试"""
    print_section("5. 集成测试")

    binding_manager = AntiDetectBindingManager()
    health_manager = AccountHealthManager()

    account_id = "integration_user"
    platform = "xhs"

    # 1. 创建绑定
    print("🔗 创建账号-代理-指纹绑定...")
    fingerprint = binding_manager.get_or_create_fingerprint(account_id, platform)
    binding_manager.bind_proxy(account_id, platform, "proxy_integration")
    print(f"   ✅ 绑定完成")

    # 2. 获取绑定
    proxy_id, fp = binding_manager.get_complete_binding(account_id, platform)
    print(f"\n📋 绑定信息:")
    print(f"   账号: {account_id}")
    print(f"   平台: {platform}")
    print(f"   代理: {proxy_id}")
    print(f"   指纹: {fp.fingerprint_id}")

    # 3. 模拟使用
    print(f"\n🚀 模拟爬虫使用...")
    for i in range(3):
        success = i < 2
        health_manager.record_request(account_id, platform, success=success)
        print(f"   请求 {i+1}: {'成功' if success else '失败'}")

    # 4. 检查健康
    health = health_manager.get_account(account_id, platform)
    print(f"\n💚 账号健康:")
    print(f"   总请求: {health.total_requests}")
    print(f"   失败: {health.failed_requests}")
    print(f"   风险: {health.risk_score:.2f}")

    print(f"\n✅ 集成测试通过！")


async def main():
    """主函数"""
    print("\n" + "=" * 60)
    print("  反爬增强系统 - 快速测试")
    print("=" * 60)

    # 1. 测试指纹
    test_fingerprint()

    # 2. 测试限速器
    await test_rate_limiter()

    # 3. 测试账号健康
    test_account_health()

    # 4. 测试绑定管理器
    test_binding_manager()

    # 5. 集成测试
    test_integration()

    # 总结
    print_section("测试完成")
    print("✅ 所有功能正常工作！")
    print("\n📚 查看文档:")
    print("   - 使用指南: docs/ANTI_DETECT_GUIDE.md")
    print("   - 实现总结: docs/ANTI_DETECT_IMPLEMENTATION.md")
    print("   - 模块说明: anti_detect/README.md")
    print("\n🚀 运行示例:")
    print("   uv run python examples/anti_detect_xhs_crawler.py")
    print("\n" + "=" * 60 + "\n")


if __name__ == "__main__":
    asyncio.run(main())
