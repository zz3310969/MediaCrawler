# -*- coding: utf-8 -*-
# @Desc    : 智能限速器 - 模拟人类行为模式

import asyncio
import random
import time
from collections import deque
from dataclasses import dataclass
from typing import Optional


@dataclass
class RateLimitConfig:
    """限速配置"""

    # 基础间隔
    min_interval: float = 2.0  # 最小请求间隔（秒）
    max_interval: float = 8.0  # 最大请求间隔（秒）

    # 行为模拟
    burst_probability: float = 0.1  # 快速连续请求的概率（模拟快速浏览）
    pause_probability: float = 0.05  # 长时间停顿的概率（模拟离开、思考）
    pause_duration: tuple = (30, 120)  # 停顿时长范围（秒）

    # 频率限制
    hourly_limit: int = 200  # 每小时最大请求数
    daily_limit: int = 2000  # 每天最大请求数

    # 时段控制（模拟人类作息）
    active_hours: tuple = (8, 23)  # 活跃时段（小时）
    night_slowdown: float = 2.0  # 夜间减速倍数


class SmartRateLimiter:
    """
    智能限速器 - 模拟人类浏览节奏

    特点:
    - 随机间隔，避免固定频率
    - 偶尔快速连续请求（模拟快速浏览）
    - 偶尔长时间停顿（模拟离开、思考）
    - 每小时/每天频率限制
    - 时段控制（夜间减速）
    """

    def __init__(self, config: Optional[RateLimitConfig] = None):
        """
        初始化限速器

        Args:
            config: 限速配置，为空则使用默认配置
        """
        self.config = config or RateLimitConfig()
        self._last_request_time = 0.0
        self._hourly_requests = deque()  # 最近1小时的请求时间戳
        self._daily_requests = deque()  # 最近1天的请求时间戳
        self._request_count = 0

    def _clean_old_records(self):
        """清理过期的请求记录"""
        now = time.time()

        # 清理超过1小时的记录
        while self._hourly_requests and now - self._hourly_requests[0] > 3600:
            self._hourly_requests.popleft()

        # 清理超过1天的记录
        while self._daily_requests and now - self._daily_requests[0] > 86400:
            self._daily_requests.popleft()

    def _is_active_hour(self) -> bool:
        """检查当前是否在活跃时段"""
        from datetime import datetime

        current_hour = datetime.now().hour
        start_hour, end_hour = self.config.active_hours
        return start_hour <= current_hour < end_hour

    def _calculate_delay(self) -> float:
        """
        计算下次请求的延迟时间

        Returns:
            float: 延迟秒数
        """
        # 基础延迟
        if random.random() < self.config.burst_probability:
            # 快速连续请求（模拟快速浏览）
            delay = random.uniform(0.5, self.config.min_interval)
        else:
            # 正常随机间隔
            delay = random.uniform(self.config.min_interval, self.config.max_interval)
            # 添加高斯噪声使间隔更自然
            delay += random.gauss(0, 0.5)
            delay = max(self.config.min_interval, delay)

        # 夜间减速
        if not self._is_active_hour():
            delay *= self.config.night_slowdown

        return delay

    async def wait(self):
        """
        等待到合适的时机再发送请求

        会自动处理:
        - 频率限制（每小时/每天）
        - 随机间隔
        - 偶尔的长时间停顿
        - 时段控制
        """
        self._clean_old_records()

        # 检查每小时频率限制
        if len(self._hourly_requests) >= self.config.hourly_limit:
            wait_time = 3600 - (time.time() - self._hourly_requests[0])
            if wait_time > 0:
                print(f"[RateLimiter] Hourly limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                self._clean_old_records()

        # 检查每日频率限制
        if len(self._daily_requests) >= self.config.daily_limit:
            wait_time = 86400 - (time.time() - self._daily_requests[0])
            if wait_time > 0:
                print(f"[RateLimiter] Daily limit reached, waiting {wait_time:.1f}s")
                await asyncio.sleep(wait_time)
                self._clean_old_records()

        # 偶尔长时间停顿（模拟离开、思考）
        if random.random() < self.config.pause_probability:
            pause = random.uniform(*self.config.pause_duration)
            print(f"[RateLimiter] Random pause for {pause:.1f}s (simulating human break)")
            await asyncio.sleep(pause)

        # 计算并等待延迟
        now = time.time()
        elapsed = now - self._last_request_time

        delay = self._calculate_delay()
        if elapsed < delay:
            wait_time = delay - elapsed
            await asyncio.sleep(wait_time)

        # 记录请求
        now = time.time()
        self._last_request_time = now
        self._hourly_requests.append(now)
        self._daily_requests.append(now)
        self._request_count += 1

    def get_stats(self) -> dict:
        """
        获取统计信息

        Returns:
            dict: 统计数据
        """
        self._clean_old_records()
        return {
            "total_requests": self._request_count,
            "hourly_requests": len(self._hourly_requests),
            "daily_requests": len(self._daily_requests),
            "hourly_limit": self.config.hourly_limit,
            "daily_limit": self.config.daily_limit,
            "is_active_hour": self._is_active_hour(),
        }

    def reset(self):
        """重置限速器"""
        self._last_request_time = 0.0
        self._hourly_requests.clear()
        self._daily_requests.clear()
        self._request_count = 0


class PlatformRateLimiter:
    """
    平台级限速器 - 为不同平台提供不同的限速策略
    """

    # 各平台推荐配置
    PLATFORM_CONFIGS = {
        "xhs": RateLimitConfig(
            min_interval=3.0,
            max_interval=10.0,
            hourly_limit=150,
            daily_limit=1500,
        ),
        "dy": RateLimitConfig(
            min_interval=2.5,
            max_interval=8.0,
            hourly_limit=180,
            daily_limit=1800,
        ),
        "wb": RateLimitConfig(
            min_interval=2.0,
            max_interval=7.0,
            hourly_limit=200,
            daily_limit=2000,
        ),
        "bili": RateLimitConfig(
            min_interval=2.0,
            max_interval=6.0,
            hourly_limit=250,
            daily_limit=2500,
        ),
        "ks": RateLimitConfig(
            min_interval=2.5,
            max_interval=8.0,
            hourly_limit=180,
            daily_limit=1800,
        ),
    }

    def __init__(self):
        """初始化平台限速器"""
        self._limiters = {}

    def get_limiter(self, platform: str) -> SmartRateLimiter:
        """
        获取指定平台的限速器

        Args:
            platform: 平台标识 (xhs, dy, wb, etc.)

        Returns:
            SmartRateLimiter: 限速器实例
        """
        if platform not in self._limiters:
            config = self.PLATFORM_CONFIGS.get(platform, RateLimitConfig())
            self._limiters[platform] = SmartRateLimiter(config)
        return self._limiters[platform]

    async def wait(self, platform: str):
        """
        等待指定平台的限速

        Args:
            platform: 平台标识
        """
        limiter = self.get_limiter(platform)
        await limiter.wait()

    def get_stats(self, platform: str) -> dict:
        """
        获取指定平台的统计信息

        Args:
            platform: 平台标识

        Returns:
            dict: 统计数据
        """
        limiter = self.get_limiter(platform)
        return limiter.get_stats()
