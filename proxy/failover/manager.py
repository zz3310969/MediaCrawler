# -*- coding: utf-8 -*-
# @Desc    : 代理故障转移管理器

import asyncio
import time
from typing import Any, Callable, Coroutine, Dict, List, Optional, TypeVar, Union

from tools.utils import utils

from ..persistence.proxy_store import ProxyStore
from ..quality.evaluator import ProxyQualityEvaluator
from ..types import IpInfoModel
from .strategy import (
    CircuitBreakerStrategy,
    FailoverStrategy,
    SimpleFailoverStrategy,
)


T = TypeVar('T')


class ProxyFailoverManager:
    """
    代理故障转移管理器
    
    功能:
    - 管理代理故障转移
    - 支持多种转移策略
    - 自动重试请求
    - 集成质量评估
    """
    
    def __init__(
        self,
        proxy_store: ProxyStore,
        strategy: Optional[FailoverStrategy] = None,
        quality_evaluator: Optional[ProxyQualityEvaluator] = None,
        max_retries: int = 3,
        retry_delay_seconds: float = 1.0,
    ):
        """
        初始化故障转移管理器
        
        Args:
            proxy_store: 代理存储
            strategy: 故障转移策略
            quality_evaluator: 质量评估器
            max_retries: 最大重试次数
            retry_delay_seconds: 重试延迟（秒）
        """
        self._proxy_store = proxy_store
        self._strategy = strategy or CircuitBreakerStrategy()
        self._quality_evaluator = quality_evaluator
        self._max_retries = max_retries
        self._retry_delay = retry_delay_seconds
        
        # 当前代理缓存
        self._current_proxy: Optional[IpInfoModel] = None
        self._available_proxies: List[IpInfoModel] = []
        self._last_refresh_time: float = 0
        self._cache_ttl_seconds: float = 60  # 代理列表缓存1分钟
    
    def set_strategy(self, strategy: FailoverStrategy) -> None:
        """设置故障转移策略"""
        self._strategy = strategy
    
    async def _refresh_proxies_if_needed(self) -> None:
        """如果需要，刷新代理列表"""
        now = time.time()
        if now - self._last_refresh_time > self._cache_ttl_seconds:
            await self._refresh_proxies()
    
    async def _refresh_proxies(self) -> None:
        """刷新代理列表"""
        persisted = await self._proxy_store.get_available_proxies(limit=50)
        self._available_proxies = [p.to_ip_info_model() for p in persisted]
        self._last_refresh_time = time.time()
        utils.logger.debug(
            f"[FailoverManager] Refreshed proxy list, count: {len(self._available_proxies)}"
        )
    
    async def get_proxy(
        self,
        failed_proxy_id: Optional[str] = None,
        protocol: Optional[str] = None,
    ) -> Optional[IpInfoModel]:
        """
        获取代理
        
        Args:
            failed_proxy_id: 上次失败的代理ID
            protocol: 协议筛选
            
        Returns:
            代理信息
        """
        await self._refresh_proxies_if_needed()
        
        # 筛选协议
        proxies = self._available_proxies
        if protocol:
            proxies = [p for p in proxies if p.protocol == protocol]
        
        if not proxies:
            return None
        
        # 使用策略选择代理
        proxy = await self._strategy.select_proxy(
            proxies=proxies,
            failed_proxy_id=failed_proxy_id,
        )
        
        if proxy:
            self._current_proxy = proxy
        
        return proxy
    
    async def execute_with_failover(
        self,
        func: Callable[..., Coroutine[Any, Any, T]],
        *args,
        proxy_kwarg: str = "proxy",
        **kwargs,
    ) -> T:
        """
        带故障转移的执行请求
        
        Args:
            func: 要执行的异步函数
            proxy_kwarg: 代理参数名
            *args, **kwargs: 函数参数
            
        Returns:
            函数返回值
            
        Raises:
            Exception: 所有重试都失败后抛出最后的异常
        """
        last_exception = None
        failed_proxy_id = None
        
        for attempt in range(self._max_retries + 1):
            # 获取代理
            proxy = await self.get_proxy(failed_proxy_id=failed_proxy_id)
            if not proxy:
                raise RuntimeError("No available proxies")
            
            # 构建代理参数
            proxy_value = proxy.to_url()
            kwargs[proxy_kwarg] = proxy_value
            
            start_time = time.time()
            
            try:
                result = await func(*args, **kwargs)
                
                # 请求成功
                response_time = (time.time() - start_time) * 1000
                self._strategy.on_success(proxy.proxy_id)
                
                if self._quality_evaluator:
                    await self._quality_evaluator.record_success(
                        proxy.proxy_id, response_time
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                failed_proxy_id = proxy.proxy_id
                
                # 记录失败
                self._strategy.on_failure(proxy.proxy_id)
                
                is_timeout = "timeout" in str(e).lower()
                if self._quality_evaluator:
                    await self._quality_evaluator.record_failure(
                        proxy.proxy_id,
                        is_timeout=is_timeout,
                        error_type=type(e).__name__,
                    )
                
                utils.logger.warning(
                    f"[FailoverManager] Request failed with proxy {proxy.ip}:{proxy.port}, "
                    f"attempt {attempt + 1}/{self._max_retries + 1}: {e}"
                )
                
                # 如果还有重试机会，等待一段时间
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_delay)
        
        # 所有重试都失败
        raise last_exception
    
    async def execute_with_proxy(
        self,
        func: Callable[[IpInfoModel], Coroutine[Any, Any, T]],
    ) -> T:
        """
        带代理执行请求（代理作为参数传递）
        
        Args:
            func: 接收代理参数的异步函数
            
        Returns:
            函数返回值
        """
        last_exception = None
        failed_proxy_id = None
        
        for attempt in range(self._max_retries + 1):
            proxy = await self.get_proxy(failed_proxy_id=failed_proxy_id)
            if not proxy:
                raise RuntimeError("No available proxies")
            
            start_time = time.time()
            
            try:
                result = await func(proxy)
                
                response_time = (time.time() - start_time) * 1000
                self._strategy.on_success(proxy.proxy_id)
                
                if self._quality_evaluator:
                    await self._quality_evaluator.record_success(
                        proxy.proxy_id, response_time
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                failed_proxy_id = proxy.proxy_id
                
                self._strategy.on_failure(proxy.proxy_id)
                
                is_timeout = "timeout" in str(e).lower()
                if self._quality_evaluator:
                    await self._quality_evaluator.record_failure(
                        proxy.proxy_id,
                        is_timeout=is_timeout,
                        error_type=type(e).__name__,
                    )
                
                utils.logger.warning(
                    f"[FailoverManager] Request failed with proxy {proxy.ip}:{proxy.port}, "
                    f"attempt {attempt + 1}/{self._max_retries + 1}: {e}"
                )
                
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_delay)
        
        raise last_exception
    
    def report_success(self, proxy_id: str, response_time_ms: float) -> None:
        """
        报告请求成功（供外部调用）
        
        Args:
            proxy_id: 代理ID
            response_time_ms: 响应时间
        """
        self._strategy.on_success(proxy_id)
    
    def report_failure(self, proxy_id: str) -> None:
        """
        报告请求失败（供外部调用）
        
        Args:
            proxy_id: 代理ID
        """
        self._strategy.on_failure(proxy_id)
    
    @property
    def current_proxy(self) -> Optional[IpInfoModel]:
        """获取当前代理"""
        return self._current_proxy
    
    @property
    def available_count(self) -> int:
        """获取可用代理数量"""
        return len(self._available_proxies)
    
    async def force_refresh(self) -> None:
        """强制刷新代理列表"""
        await self._refresh_proxies()
    
    def clear_cache(self) -> None:
        """清除缓存"""
        self._available_proxies.clear()
        self._current_proxy = None
        self._last_refresh_time = 0

