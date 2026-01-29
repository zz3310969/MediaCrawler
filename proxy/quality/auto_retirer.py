# -*- coding: utf-8 -*-
# @Desc    : 自动代理淘汰器

import asyncio
from datetime import datetime
from typing import Callable, List, Optional

from tools.utils import utils

from ..persistence.proxy_store import ProxyStore
from ..persistence.binding_store import BindingStore
from ..types import PersistedProxy, ProxyQualityMetrics
from .evaluator import ProxyQualityEvaluator


class AutoProxyRetirer:
    """
    自动代理淘汰器
    
    功能:
    - 定期检查代理质量
    - 自动淘汰低质量代理
    - 触发相关绑定的重绑定
    """
    
    def __init__(
        self,
        proxy_store: ProxyStore,
        binding_store: BindingStore,
        evaluator: ProxyQualityEvaluator,
        min_quality_score: float = 30,
        min_requests_for_retire: int = 20,
        max_consecutive_failures: int = 10,
        check_interval_seconds: int = 300,  # 5分钟
        on_proxy_retired: Optional[Callable[[str], None]] = None,
    ):
        """
        初始化淘汰器
        
        Args:
            proxy_store: 代理存储
            binding_store: 绑定存储
            evaluator: 质量评估器
            min_quality_score: 最低质量分
            min_requests_for_retire: 淘汰所需最小请求数
            max_consecutive_failures: 最大连续失败次数
            check_interval_seconds: 检查间隔（秒）
            on_proxy_retired: 代理被淘汰时的回调
        """
        self._proxy_store = proxy_store
        self._binding_store = binding_store
        self._evaluator = evaluator
        
        self._min_quality_score = min_quality_score
        self._min_requests = min_requests_for_retire
        self._max_consecutive_failures = max_consecutive_failures
        self._check_interval = check_interval_seconds
        self._on_proxy_retired = on_proxy_retired
        
        self._running = False
        self._task: Optional[asyncio.Task] = None
    
    async def start(self) -> None:
        """启动自动检查"""
        if self._running:
            return
        
        self._running = True
        self._task = asyncio.create_task(self._check_loop())
        utils.logger.info("[AutoProxyRetirer] Started automatic proxy retirement check")
    
    async def stop(self) -> None:
        """停止自动检查"""
        self._running = False
        if self._task:
            self._task.cancel()
            try:
                await self._task
            except asyncio.CancelledError:
                pass
        utils.logger.info("[AutoProxyRetirer] Stopped automatic proxy retirement check")
    
    async def _check_loop(self) -> None:
        """检查循环"""
        while self._running:
            try:
                await self.check_and_retire()
            except Exception as e:
                utils.logger.error(f"[AutoProxyRetirer] Check failed: {e}")
            
            await asyncio.sleep(self._check_interval)
    
    async def check_and_retire(self) -> List[str]:
        """
        检查并淘汰低质量代理
        
        Returns:
            被淘汰的代理ID列表
        """
        retired_ids = []
        
        # 获取所有活跃代理
        proxies = await self._proxy_store.get_all_proxies(is_active=True)
        
        for proxy in proxies:
            should_retire = await self._should_retire_proxy(proxy)
            if should_retire:
                await self._retire_proxy(proxy)
                retired_ids.append(proxy.proxy_id)
        
        if retired_ids:
            utils.logger.info(f"[AutoProxyRetirer] Retired {len(retired_ids)} proxies")
        
        return retired_ids
    
    async def _should_retire_proxy(self, proxy: PersistedProxy) -> bool:
        """
        判断代理是否应该被淘汰
        
        Args:
            proxy: 代理对象
            
        Returns:
            是否应该淘汰
        """
        # 获取质量指标
        metrics = await self._evaluator.get_metrics(proxy.proxy_id)
        
        # 检查连续失败次数
        if metrics.consecutive_failures >= self._max_consecutive_failures:
            utils.logger.warning(
                f"[AutoProxyRetirer] Proxy {proxy.proxy_id} has {metrics.consecutive_failures} "
                f"consecutive failures, marking for retirement"
            )
            return True
        
        # 检查质量分（需要足够的请求量）
        if metrics.total_requests >= self._min_requests:
            if metrics.quality_score < self._min_quality_score:
                utils.logger.warning(
                    f"[AutoProxyRetirer] Proxy {proxy.proxy_id} quality score "
                    f"{metrics.quality_score:.1f} < {self._min_quality_score}, marking for retirement"
                )
                return True
        
        return False
    
    async def _retire_proxy(self, proxy: PersistedProxy) -> None:
        """
        淘汰代理
        
        Args:
            proxy: 代理对象
        """
        proxy_id = proxy.proxy_id
        
        # 标记代理为不可用
        await self._proxy_store.update_proxy_status(proxy_id, is_active=False)
        
        # 获取使用该代理的所有绑定
        bindings = await self._binding_store.get_bindings_by_proxy(proxy_id)
        
        # 标记绑定为过期（让绑定管理器在下次使用时自动重绑）
        for binding in bindings:
            await self._binding_store.update_binding_status(
                binding.account_id,
                binding.platform,
                "expired",
            )
            utils.logger.info(
                f"[AutoProxyRetirer] Marked binding for account {binding.account_id}@{binding.platform} "
                f"as expired due to proxy retirement"
            )
        
        # 触发回调
        if self._on_proxy_retired:
            try:
                self._on_proxy_retired(proxy_id)
            except Exception as e:
                utils.logger.error(f"[AutoProxyRetirer] Callback error: {e}")
        
        utils.logger.info(
            f"[AutoProxyRetirer] Retired proxy {proxy_id}, "
            f"affected bindings: {len(bindings)}"
        )
    
    async def force_retire(self, proxy_id: str, reason: str = "手动淘汰") -> bool:
        """
        强制淘汰代理
        
        Args:
            proxy_id: 代理ID
            reason: 淘汰原因
            
        Returns:
            是否成功
        """
        proxy = await self._proxy_store.get_proxy(proxy_id)
        if not proxy:
            return False
        
        utils.logger.info(f"[AutoProxyRetirer] Force retiring proxy {proxy_id}: {reason}")
        await self._retire_proxy(proxy)
        return True
    
    async def get_retirement_candidates(self) -> List[PersistedProxy]:
        """
        获取待淘汰代理列表
        
        Returns:
            待淘汰的代理列表
        """
        candidates = []
        proxies = await self._proxy_store.get_all_proxies(is_active=True)
        
        for proxy in proxies:
            if await self._should_retire_proxy(proxy):
                candidates.append(proxy)
        
        return candidates
    
    async def get_low_quality_proxies(
        self,
        threshold: Optional[float] = None,
    ) -> List[tuple]:
        """
        获取低质量代理列表
        
        Args:
            threshold: 质量分阈值，默认使用配置值
            
        Returns:
            (代理, 质量指标) 元组列表
        """
        threshold = threshold or self._min_quality_score
        result = []
        
        proxies = await self._proxy_store.get_all_proxies(is_active=True)
        
        for proxy in proxies:
            metrics = await self._evaluator.get_metrics(proxy.proxy_id)
            if metrics.quality_score < threshold:
                result.append((proxy, metrics))
        
        # 按质量分排序
        result.sort(key=lambda x: x[1].quality_score)
        return result

