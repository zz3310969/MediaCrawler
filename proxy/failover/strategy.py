# -*- coding: utf-8 -*-
# @Desc    : 故障转移策略

import random
import time
from abc import ABC, abstractmethod
from dataclasses import dataclass, field
from enum import Enum
from typing import Dict, List, Optional

from tools.utils import utils

from ..types import IpInfoModel, ProxyQualityMetrics


class CircuitState(Enum):
    """熔断器状态"""
    CLOSED = "closed"         # 关闭状态（正常工作）
    OPEN = "open"             # 开启状态（熔断中，拒绝请求）
    HALF_OPEN = "half_open"   # 半开状态（允许部分请求测试）


@dataclass
class CircuitBreakerState:
    """熔断器状态"""
    proxy_id: str
    state: CircuitState = CircuitState.CLOSED
    failure_count: int = 0
    success_count: int = 0
    last_failure_time: float = 0
    last_state_change_time: float = field(default_factory=time.time)
    
    def reset(self) -> None:
        """重置状态"""
        self.state = CircuitState.CLOSED
        self.failure_count = 0
        self.success_count = 0


class FailoverStrategy(ABC):
    """故障转移策略基类"""
    
    @abstractmethod
    async def select_proxy(
        self,
        proxies: List[IpInfoModel],
        failed_proxy_id: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> Optional[IpInfoModel]:
        """
        选择代理
        
        Args:
            proxies: 可用代理列表
            failed_proxy_id: 失败的代理ID
            context: 上下文信息
            
        Returns:
            选中的代理，无可用返回None
        """
        raise NotImplementedError
    
    @abstractmethod
    def on_success(self, proxy_id: str) -> None:
        """代理请求成功回调"""
        raise NotImplementedError
    
    @abstractmethod
    def on_failure(self, proxy_id: str) -> None:
        """代理请求失败回调"""
        raise NotImplementedError


class SimpleFailoverStrategy(FailoverStrategy):
    """
    简单故障转移策略
    
    失败后直接切换到下一个可用代理
    """
    
    def __init__(self, max_retries: int = 3):
        self._max_retries = max_retries
        self._failed_proxies: Dict[str, int] = {}  # proxy_id -> retry_count
    
    async def select_proxy(
        self,
        proxies: List[IpInfoModel],
        failed_proxy_id: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> Optional[IpInfoModel]:
        if not proxies:
            return None
        
        # 过滤掉达到最大重试次数的代理
        available = [
            p for p in proxies
            if self._failed_proxies.get(p.proxy_id, 0) < self._max_retries
        ]
        
        if not available:
            # 重置所有计数，重新开始
            self._failed_proxies.clear()
            available = proxies
        
        # 如果有失败的代理，优先选择其他代理
        if failed_proxy_id:
            other_proxies = [p for p in available if p.proxy_id != failed_proxy_id]
            if other_proxies:
                available = other_proxies
        
        return available[0] if available else None
    
    def on_success(self, proxy_id: str) -> None:
        # 成功后清除失败计数
        self._failed_proxies.pop(proxy_id, None)
    
    def on_failure(self, proxy_id: str) -> None:
        self._failed_proxies[proxy_id] = self._failed_proxies.get(proxy_id, 0) + 1


class StickyFailoverStrategy(FailoverStrategy):
    """
    粘性故障转移策略
    
    尽量使用同一个代理，只有连续失败多次后才切换
    """
    
    def __init__(
        self,
        failure_threshold: int = 3,
        recovery_time_seconds: int = 300,
    ):
        self._failure_threshold = failure_threshold
        self._recovery_time = recovery_time_seconds
        self._failure_counts: Dict[str, int] = {}
        self._blocked_until: Dict[str, float] = {}
        self._current_proxy_id: Optional[str] = None
    
    async def select_proxy(
        self,
        proxies: List[IpInfoModel],
        failed_proxy_id: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> Optional[IpInfoModel]:
        if not proxies:
            return None
        
        now = time.time()
        
        # 清理过期的阻塞
        self._blocked_until = {
            k: v for k, v in self._blocked_until.items() if v > now
        }
        
        # 过滤掉被阻塞的代理
        available = [
            p for p in proxies
            if p.proxy_id not in self._blocked_until
        ]
        
        if not available:
            # 所有代理都被阻塞，选择阻塞时间最短的
            min_blocked_id = min(
                self._blocked_until.keys(),
                key=lambda k: self._blocked_until[k]
            )
            for p in proxies:
                if p.proxy_id == min_blocked_id:
                    return p
            return proxies[0]
        
        # 如果当前代理可用，继续使用
        if self._current_proxy_id:
            for p in available:
                if p.proxy_id == self._current_proxy_id:
                    return p
        
        # 选择第一个可用代理
        selected = available[0]
        self._current_proxy_id = selected.proxy_id
        return selected
    
    def on_success(self, proxy_id: str) -> None:
        self._failure_counts[proxy_id] = 0
        self._current_proxy_id = proxy_id
    
    def on_failure(self, proxy_id: str) -> None:
        self._failure_counts[proxy_id] = self._failure_counts.get(proxy_id, 0) + 1
        
        if self._failure_counts[proxy_id] >= self._failure_threshold:
            # 阻塞该代理一段时间
            self._blocked_until[proxy_id] = time.time() + self._recovery_time
            self._failure_counts[proxy_id] = 0
            
            # 清除当前代理
            if self._current_proxy_id == proxy_id:
                self._current_proxy_id = None
            
            utils.logger.warning(
                f"[StickyFailover] Proxy {proxy_id} blocked for {self._recovery_time}s "
                f"after {self._failure_threshold} failures"
            )


class WeightedFailoverStrategy(FailoverStrategy):
    """
    加权故障转移策略
    
    根据代理质量分配权重，高质量代理更容易被选中
    """
    
    def __init__(self, quality_metrics: Optional[Dict[str, ProxyQualityMetrics]] = None):
        self._quality_metrics = quality_metrics or {}
        self._failure_penalty = 10  # 每次失败减少的权重
    
    def set_quality_metrics(self, metrics: Dict[str, ProxyQualityMetrics]) -> None:
        """设置质量指标"""
        self._quality_metrics = metrics
    
    def _get_weight(self, proxy: IpInfoModel) -> float:
        """获取代理权重"""
        metrics = self._quality_metrics.get(proxy.proxy_id)
        if metrics:
            # 使用质量分作为权重基础
            return max(1, metrics.quality_score)
        # 默认权重100（满分）
        return 100.0
    
    async def select_proxy(
        self,
        proxies: List[IpInfoModel],
        failed_proxy_id: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> Optional[IpInfoModel]:
        if not proxies:
            return None
        
        # 计算权重
        weights = []
        for p in proxies:
            weight = self._get_weight(p)
            # 对失败的代理降低权重
            if p.proxy_id == failed_proxy_id:
                weight = max(1, weight - self._failure_penalty)
            weights.append(weight)
        
        # 加权随机选择
        total_weight = sum(weights)
        if total_weight <= 0:
            return proxies[0]
        
        r = random.uniform(0, total_weight)
        cumulative = 0
        for i, weight in enumerate(weights):
            cumulative += weight
            if r <= cumulative:
                return proxies[i]
        
        return proxies[-1]
    
    def on_success(self, proxy_id: str) -> None:
        # 成功时可以提升权重，但这里由质量评估器处理
        pass
    
    def on_failure(self, proxy_id: str) -> None:
        # 失败时可以降低权重，但这里由质量评估器处理
        pass


class CircuitBreakerStrategy(FailoverStrategy):
    """
    熔断器故障转移策略
    
    实现熔断器模式:
    - CLOSED: 正常状态，请求通过
    - OPEN: 熔断状态，拒绝请求
    - HALF_OPEN: 半开状态，允许部分请求测试
    
    状态转换:
    - CLOSED -> OPEN: 连续失败达到阈值
    - OPEN -> HALF_OPEN: 经过恢复时间
    - HALF_OPEN -> CLOSED: 测试请求成功
    - HALF_OPEN -> OPEN: 测试请求失败
    """
    
    def __init__(
        self,
        failure_threshold: int = 5,
        recovery_timeout_seconds: int = 60,
        half_open_max_calls: int = 3,
    ):
        """
        初始化熔断器
        
        Args:
            failure_threshold: 触发熔断的连续失败次数
            recovery_timeout_seconds: 熔断恢复时间（秒）
            half_open_max_calls: 半开状态最大测试调用数
        """
        self._failure_threshold = failure_threshold
        self._recovery_timeout = recovery_timeout_seconds
        self._half_open_max_calls = half_open_max_calls
        
        self._breakers: Dict[str, CircuitBreakerState] = {}
    
    def _get_or_create_breaker(self, proxy_id: str) -> CircuitBreakerState:
        """获取或创建熔断器状态"""
        if proxy_id not in self._breakers:
            self._breakers[proxy_id] = CircuitBreakerState(proxy_id=proxy_id)
        return self._breakers[proxy_id]
    
    def _update_state(self, breaker: CircuitBreakerState) -> None:
        """更新熔断器状态"""
        now = time.time()
        
        if breaker.state == CircuitState.OPEN:
            # 检查是否可以转为半开状态
            if now - breaker.last_state_change_time >= self._recovery_timeout:
                breaker.state = CircuitState.HALF_OPEN
                breaker.last_state_change_time = now
                breaker.success_count = 0
                utils.logger.info(
                    f"[CircuitBreaker] Proxy {breaker.proxy_id} state: OPEN -> HALF_OPEN"
                )
    
    def _is_allowed(self, breaker: CircuitBreakerState) -> bool:
        """检查是否允许请求"""
        self._update_state(breaker)
        
        if breaker.state == CircuitState.CLOSED:
            return True
        elif breaker.state == CircuitState.OPEN:
            return False
        else:  # HALF_OPEN
            return breaker.success_count < self._half_open_max_calls
    
    async def select_proxy(
        self,
        proxies: List[IpInfoModel],
        failed_proxy_id: Optional[str] = None,
        context: Optional[Dict] = None,
    ) -> Optional[IpInfoModel]:
        if not proxies:
            return None
        
        # 过滤掉熔断开启的代理
        available = []
        for p in proxies:
            breaker = self._get_or_create_breaker(p.proxy_id)
            if self._is_allowed(breaker):
                available.append(p)
        
        if not available:
            # 所有代理都熔断了，选择最早进入熔断的（最可能恢复）
            earliest_id = min(
                self._breakers.keys(),
                key=lambda k: self._breakers[k].last_state_change_time
            )
            for p in proxies:
                if p.proxy_id == earliest_id:
                    return p
            return proxies[0]
        
        # 优先选择 CLOSED 状态的代理
        closed_proxies = [
            p for p in available
            if self._get_or_create_breaker(p.proxy_id).state == CircuitState.CLOSED
        ]
        
        if closed_proxies:
            # 如果有失败的代理，优先选择其他代理
            if failed_proxy_id:
                other_proxies = [p for p in closed_proxies if p.proxy_id != failed_proxy_id]
                if other_proxies:
                    return other_proxies[0]
            return closed_proxies[0]
        
        # 返回第一个可用的（HALF_OPEN状态）
        return available[0]
    
    def on_success(self, proxy_id: str) -> None:
        breaker = self._get_or_create_breaker(proxy_id)
        
        if breaker.state == CircuitState.HALF_OPEN:
            breaker.success_count += 1
            if breaker.success_count >= self._half_open_max_calls:
                # 测试成功，恢复到关闭状态
                breaker.state = CircuitState.CLOSED
                breaker.last_state_change_time = time.time()
                breaker.failure_count = 0
                utils.logger.info(
                    f"[CircuitBreaker] Proxy {proxy_id} state: HALF_OPEN -> CLOSED"
                )
        else:
            # CLOSED 状态成功，重置失败计数
            breaker.failure_count = 0
    
    def on_failure(self, proxy_id: str) -> None:
        breaker = self._get_or_create_breaker(proxy_id)
        breaker.last_failure_time = time.time()
        
        if breaker.state == CircuitState.HALF_OPEN:
            # 半开状态失败，立即熔断
            breaker.state = CircuitState.OPEN
            breaker.last_state_change_time = time.time()
            utils.logger.warning(
                f"[CircuitBreaker] Proxy {proxy_id} state: HALF_OPEN -> OPEN "
                f"(test failed)"
            )
        elif breaker.state == CircuitState.CLOSED:
            breaker.failure_count += 1
            if breaker.failure_count >= self._failure_threshold:
                # 达到阈值，熔断
                breaker.state = CircuitState.OPEN
                breaker.last_state_change_time = time.time()
                utils.logger.warning(
                    f"[CircuitBreaker] Proxy {proxy_id} state: CLOSED -> OPEN "
                    f"(failures: {breaker.failure_count})"
                )
    
    def get_state(self, proxy_id: str) -> CircuitState:
        """获取代理的熔断状态"""
        breaker = self._get_or_create_breaker(proxy_id)
        self._update_state(breaker)
        return breaker.state
    
    def reset(self, proxy_id: str) -> None:
        """重置代理的熔断状态"""
        if proxy_id in self._breakers:
            self._breakers[proxy_id].reset()
            utils.logger.info(f"[CircuitBreaker] Proxy {proxy_id} reset to CLOSED")
    
    def reset_all(self) -> None:
        """重置所有熔断器"""
        for breaker in self._breakers.values():
            breaker.reset()
        utils.logger.info("[CircuitBreaker] All breakers reset to CLOSED")

