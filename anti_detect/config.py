# -*- coding: utf-8 -*-
# @Desc    : 反爬增强配置

from dataclasses import dataclass
from typing import Optional


@dataclass
class AntiDetectConfig:
    """反爬增强配置"""

    # 功能开关
    enable_fingerprint: bool = True  # 启用浏览器指纹
    enable_rate_limit: bool = True  # 启用智能限速
    enable_human_behavior: bool = True  # 启用人类行为模拟
    enable_account_health: bool = True  # 启用账号健康管理
    enable_binding: bool = True  # 启用账号-代理-指纹绑定

    # 指纹配置
    fingerprint_platform_hint: Optional[str] = None  # 平台提示 ("mac", "windows", "linux")
    fingerprint_storage_path: str = "data/fingerprints.json"

    # 限速配置
    rate_limit_min_interval: float = 2.0  # 最小请求间隔（秒）
    rate_limit_max_interval: float = 8.0  # 最大请求间隔（秒）
    rate_limit_hourly_limit: int = 200  # 每小时最大请求数
    rate_limit_daily_limit: int = 2000  # 每天最大请求数

    # 人类行为配置
    human_scroll_enabled: bool = True  # 启用人类滚动
    human_click_enabled: bool = True  # 启用人类点击
    human_browse_duration: float = 5.0  # 随机浏览时长（秒）

    # 账号健康配置
    account_health_storage_path: str = "data/account_health.json"
    account_cooling_threshold: float = 70.0  # 冷却阈值（风险评分）
    account_warning_threshold: float = 50.0  # 警告阈值（风险评分）

    # 绑定配置
    binding_storage_path: str = "data/anti_detect_bindings.json"
    binding_auto_create_fingerprint: bool = True  # 自动创建指纹
    binding_sticky_proxy: bool = True  # 粘性代理（保持绑定）


# 各平台推荐配置
PLATFORM_CONFIGS = {
    "xhs": AntiDetectConfig(
        rate_limit_min_interval=3.0,
        rate_limit_max_interval=10.0,
        rate_limit_hourly_limit=150,
        rate_limit_daily_limit=1500,
    ),
    "dy": AntiDetectConfig(
        rate_limit_min_interval=2.5,
        rate_limit_max_interval=8.0,
        rate_limit_hourly_limit=180,
        rate_limit_daily_limit=1800,
    ),
    "wb": AntiDetectConfig(
        rate_limit_min_interval=2.0,
        rate_limit_max_interval=7.0,
        rate_limit_hourly_limit=200,
        rate_limit_daily_limit=2000,
    ),
    "bili": AntiDetectConfig(
        rate_limit_min_interval=2.0,
        rate_limit_max_interval=6.0,
        rate_limit_hourly_limit=250,
        rate_limit_daily_limit=2500,
    ),
    "ks": AntiDetectConfig(
        rate_limit_min_interval=2.5,
        rate_limit_max_interval=8.0,
        rate_limit_hourly_limit=180,
        rate_limit_daily_limit=1800,
    ),
}


def get_platform_config(platform: str) -> AntiDetectConfig:
    """
    获取平台推荐配置

    Args:
        platform: 平台标识

    Returns:
        AntiDetectConfig: 配置对象
    """
    return PLATFORM_CONFIGS.get(platform, AntiDetectConfig())
