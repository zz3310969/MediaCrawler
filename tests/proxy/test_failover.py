# -*- coding: utf-8 -*-
# @Desc    : 故障转移策略测试

import pytest
import asyncio
import time

from proxy.types import IpInfoModel
from proxy.failover.strategy import (
    SimpleFailoverStrategy,
    StickyFailoverStrategy,
    CircuitBreakerStrategy,
    CircuitState,
)


@pytest.fixture
def sample_proxies():
    """创建测试用代理列表"""
    return [
        IpInfoModel(ip="192.168.1.1", port=8080, proxy_id="proxy1"),
        IpInfoModel(ip="192.168.1.2", port=8080, proxy_id="proxy2"),
        IpInfoModel(ip="192.168.1.3", port=8080, proxy_id="proxy3"),
    ]


class TestSimpleFailoverStrategy:
    """SimpleFailoverStrategy 测试"""
    
    @pytest.mark.asyncio
    async def test_select_proxy(self, sample_proxies):
        """测试代理选择"""
        strategy = SimpleFailoverStrategy()
        proxy = await strategy.select_proxy(sample_proxies)
        assert proxy is not None
        assert proxy in sample_proxies
    
    @pytest.mark.asyncio
    async def test_avoid_failed_proxy(self, sample_proxies):
        """测试避开失败的代理"""
        strategy = SimpleFailoverStrategy()
        
        # 选择一个代理
        first = await strategy.select_proxy(sample_proxies)
        
        # 标记失败
        strategy.on_failure(first.proxy_id)
        
        # 下次选择应该避开失败的代理
        second = await strategy.select_proxy(sample_proxies, failed_proxy_id=first.proxy_id)
        assert second.proxy_id != first.proxy_id
    
    @pytest.mark.asyncio
    async def test_reset_on_success(self, sample_proxies):
        """测试成功后重置失败计数"""
        strategy = SimpleFailoverStrategy()
        
        proxy = await strategy.select_proxy(sample_proxies)
        strategy.on_failure(proxy.proxy_id)
        strategy.on_failure(proxy.proxy_id)
        
        assert strategy._failed_proxies.get(proxy.proxy_id, 0) == 2
        
        strategy.on_success(proxy.proxy_id)
        assert strategy._failed_proxies.get(proxy.proxy_id, 0) == 0
    
    @pytest.mark.asyncio
    async def test_max_retries_reset(self, sample_proxies):
        """测试达到最大重试后重置"""
        strategy = SimpleFailoverStrategy(max_retries=2)
        
        # 让所有代理都达到最大重试次数
        for proxy in sample_proxies:
            for _ in range(3):
                strategy.on_failure(proxy.proxy_id)
        
        # 应该重置并重新选择
        selected = await strategy.select_proxy(sample_proxies)
        assert selected is not None


class TestStickyFailoverStrategy:
    """StickyFailoverStrategy 测试"""
    
    @pytest.mark.asyncio
    async def test_sticky_selection(self, sample_proxies):
        """测试粘性选择"""
        strategy = StickyFailoverStrategy()
        
        first = await strategy.select_proxy(sample_proxies)
        strategy.on_success(first.proxy_id)
        
        # 连续选择应该是同一个代理
        second = await strategy.select_proxy(sample_proxies)
        assert second.proxy_id == first.proxy_id
    
    @pytest.mark.asyncio
    async def test_switch_on_failures(self, sample_proxies):
        """测试达到阈值后切换"""
        strategy = StickyFailoverStrategy(
            failure_threshold=2,
            recovery_time_seconds=10,
        )
        
        first = await strategy.select_proxy(sample_proxies)
        
        # 触发2次失败，达到阈值
        strategy.on_failure(first.proxy_id)
        strategy.on_failure(first.proxy_id)
        
        # 应该被阻塞，选择其他代理
        second = await strategy.select_proxy(sample_proxies)
        assert second.proxy_id != first.proxy_id


class TestCircuitBreakerStrategy:
    """CircuitBreakerStrategy 测试"""
    
    @pytest.mark.asyncio
    async def test_initial_state(self, sample_proxies):
        """测试初始状态为CLOSED"""
        strategy = CircuitBreakerStrategy()
        
        proxy = await strategy.select_proxy(sample_proxies)
        state = strategy.get_state(proxy.proxy_id)
        assert state == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_open_on_failures(self, sample_proxies):
        """测试连续失败后熔断"""
        strategy = CircuitBreakerStrategy(failure_threshold=3)
        
        proxy = await strategy.select_proxy(sample_proxies)
        
        # 触发3次失败
        for _ in range(3):
            strategy.on_failure(proxy.proxy_id)
        
        # 状态应该变为OPEN
        assert strategy.get_state(proxy.proxy_id) == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_recovery_to_half_open(self, sample_proxies):
        """测试恢复到半开状态"""
        strategy = CircuitBreakerStrategy(
            failure_threshold=3,
            recovery_timeout_seconds=0.1,  # 0.1秒超时
        )
        
        proxy = await strategy.select_proxy(sample_proxies)
        
        # 触发熔断
        for _ in range(3):
            strategy.on_failure(proxy.proxy_id)
        
        assert strategy.get_state(proxy.proxy_id) == CircuitState.OPEN
        
        # 等待恢复
        await asyncio.sleep(0.15)
        
        # 状态应该变为HALF_OPEN
        assert strategy.get_state(proxy.proxy_id) == CircuitState.HALF_OPEN
    
    @pytest.mark.asyncio
    async def test_close_on_success_in_half_open(self, sample_proxies):
        """测试半开状态成功后关闭"""
        strategy = CircuitBreakerStrategy(
            failure_threshold=3,
            recovery_timeout_seconds=0.1,
            half_open_max_calls=2,
        )
        
        proxy = await strategy.select_proxy(sample_proxies)
        
        # 触发熔断
        for _ in range(3):
            strategy.on_failure(proxy.proxy_id)
        
        # 等待恢复到半开
        await asyncio.sleep(0.15)
        assert strategy.get_state(proxy.proxy_id) == CircuitState.HALF_OPEN
        
        # 成功2次
        strategy.on_success(proxy.proxy_id)
        strategy.on_success(proxy.proxy_id)
        
        # 应该恢复到CLOSED
        assert strategy.get_state(proxy.proxy_id) == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_reopen_on_failure_in_half_open(self, sample_proxies):
        """测试半开状态失败后重新熔断"""
        strategy = CircuitBreakerStrategy(
            failure_threshold=3,
            recovery_timeout_seconds=0.1,
        )
        
        proxy = await strategy.select_proxy(sample_proxies)
        
        # 触发熔断
        for _ in range(3):
            strategy.on_failure(proxy.proxy_id)
        
        # 等待恢复到半开
        await asyncio.sleep(0.15)
        assert strategy.get_state(proxy.proxy_id) == CircuitState.HALF_OPEN
        
        # 在半开状态失败
        strategy.on_failure(proxy.proxy_id)
        
        # 应该重新熔断
        assert strategy.get_state(proxy.proxy_id) == CircuitState.OPEN
    
    @pytest.mark.asyncio
    async def test_reset(self, sample_proxies):
        """测试重置熔断器"""
        strategy = CircuitBreakerStrategy(failure_threshold=3)
        
        proxy = await strategy.select_proxy(sample_proxies)
        
        # 触发熔断
        for _ in range(3):
            strategy.on_failure(proxy.proxy_id)
        
        assert strategy.get_state(proxy.proxy_id) == CircuitState.OPEN
        
        # 重置
        strategy.reset(proxy.proxy_id)
        assert strategy.get_state(proxy.proxy_id) == CircuitState.CLOSED
    
    @pytest.mark.asyncio
    async def test_prefer_closed_proxies(self, sample_proxies):
        """测试优先选择CLOSED状态的代理"""
        strategy = CircuitBreakerStrategy(failure_threshold=3)
        
        # 让第一个代理熔断
        for _ in range(3):
            strategy.on_failure(sample_proxies[0].proxy_id)
        
        # 选择代理应该避开熔断的
        selected = await strategy.select_proxy(sample_proxies)
        assert selected.proxy_id != sample_proxies[0].proxy_id

