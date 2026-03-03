#!/usr/bin/env python
# -*- coding: utf-8 -*-
"""
测试反爬增强 WebUI 集成

运行方式:
    uv run python examples/test_anti_detect_webui.py
"""

import sys
from pathlib import Path

# 添加项目根目录到路径
sys.path.insert(0, str(Path(__file__).parent.parent))

import asyncio
from anti_detect import (
    AntiDetectBindingManager,
    AccountHealthManager,
    FingerprintGenerator,
)


async def test_webui_integration():
    """测试 WebUI 集成"""
    print("\n" + "=" * 60)
    print("  测试反爬增强 WebUI 集成")
    print("=" * 60 + "\n")

    # 1. 创建测试数据
    print("1. 创建测试数据...")
    binding_manager = AntiDetectBindingManager()
    health_manager = AccountHealthManager()

    # 为小红书平台创建测试账号
    platform = "xhs"
    accounts = ["test_user_1", "test_user_2", "test_user_3"]

    for account_id in accounts:
        # 创建指纹绑定
        fingerprint = binding_manager.get_or_create_fingerprint(account_id, platform)
        print(f"   ✓ 账号 {account_id}: 指纹 {fingerprint.fingerprint_id[:8]}...")

        # 绑定代理
        proxy_id = f"proxy_{account_id}"
        binding_manager.bind_proxy(account_id, platform, proxy_id)
        print(f"   ✓ 账号 {account_id}: 代理 {proxy_id}")

        # 模拟一些请求
        for i in range(10):
            success = i < 8  # 80% 成功率
            health_manager.record_request(account_id, platform, success=success)

    print("\n2. 测试统计 API...")

    # 获取绑定统计
    binding_stats = binding_manager.get_stats(platform)
    print(f"\n   绑定统计:")
    print(f"   - 总绑定数: {binding_stats['total_bindings']}")
    print(f"   - 有代理: {binding_stats['with_proxy']}")
    print(f"   - 有指纹: {binding_stats['with_fingerprint']}")
    print(f"   - 完整绑定: {binding_stats['complete_bindings']}")

    # 获取账号健康统计
    health_stats = health_manager.get_stats(platform)
    print(f"\n   账号健康统计:")
    print(f"   - 总账号数: {health_stats['total_accounts']}")
    print(f"   - 活跃账号: {health_stats['active_accounts']}")
    print(f"   - 冷却账号: {health_stats['cooling_accounts']}")
    print(f"   - 平均风险: {health_stats['avg_risk_score']:.2f}")

    print("\n3. 测试列表 API...")

    # 列出绑定
    bindings = binding_manager.list_bindings(platform)
    print(f"\n   绑定列表 ({len(bindings)} 条):")
    for binding in bindings[:3]:
        print(f"   - {binding.account_id}: proxy={binding.proxy_id}, fp={binding.fingerprint_id[:8]}...")

    # 列出账号健康
    accounts_health = health_manager.list_accounts(platform)
    print(f"\n   账号健康列表 ({len(accounts_health)} 条):")
    for health in accounts_health[:3]:
        print(
            f"   - {health.account_id}: "
            f"请求={health.total_requests}, "
            f"失败={health.failed_requests}, "
            f"风险={health.risk_score:.2f}, "
            f"状态={health.status}"
        )

    print("\n4. 测试删除 API...")
    test_account = "test_user_1"
    binding_manager.remove_binding(test_account, platform)
    print(f"   ✓ 删除绑定: {test_account}")

    # 验证删除
    binding = binding_manager.get_binding(test_account, platform)
    if binding is None:
        print(f"   ✓ 验证成功: 绑定已删除")
    else:
        print(f"   ✗ 验证失败: 绑定仍然存在")

    print("\n" + "=" * 60)
    print("  测试完成")
    print("=" * 60 + "\n")

    print("📚 下一步:")
    print("   1. 启动 API 服务器:")
    print("      uv run uvicorn api.main:app --port 8080 --reload")
    print("\n   2. 启动前端开发服务器:")
    print("      cd webui-src && npm run dev")
    print("\n   3. 访问 http://localhost:5173 测试 WebUI")
    print("\n   4. API 端点:")
    print("      - GET  /api/anti-detect/stats/xhs")
    print("      - GET  /api/anti-detect/accounts/xhs")
    print("      - GET  /api/anti-detect/bindings/xhs")
    print("      - POST /api/anti-detect/bindings/xhs/{account_id}/proxy")
    print("      - DELETE /api/anti-detect/bindings/xhs/{account_id}")
    print()


if __name__ == "__main__":
    asyncio.run(test_webui_integration())
