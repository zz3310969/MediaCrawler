# -*- coding: utf-8 -*-
# Copyright (c) 2025 relakkes@gmail.com
#
# This file is part of MediaCrawler project.
# Repository: https://github.com/NanmiCoder/MediaCrawler
# GitHub: https://github.com/NanmiCoder
# Licensed under NON-COMMERCIAL LEARNING LICENSE 1.1
#

# 声明：本代码仅供学习和研究目的使用。使用者应遵守以下原则：
# 1. 不得用于任何商业用途。
# 2. 使用时应遵守目标平台的使用条款和robots.txt规则。
# 3. 不得进行大规模爬取或对平台造成运营干扰。
# 4. 应合理控制请求频率，避免给目标平台带来不必要的负担。
# 5. 不得用于任何非法或不当的用途。
#
# 详细许可条款请参阅项目根目录下的LICENSE文件。
# 使用本代码即表示您同意遵守上述原则和LICENSE中的所有条款。


# -*- coding: utf-8 -*-
# @Author  : relakkes@gmail.com
# @Time    : 2025/11/25
# @Desc    : Auto-refresh proxy Mixin class for use by various platform clients

import asyncio
import time
from typing import TYPE_CHECKING, Any, Callable, Coroutine, Optional, TypeVar

from tools import utils

if TYPE_CHECKING:
    from proxy.proxy_ip_pool import ProxyIpPool
    from proxy.failover.manager import ProxyFailoverManager
    from proxy.quality.evaluator import ProxyQualityEvaluator
    from proxy.types import IpInfoModel


T = TypeVar('T')


class ProxyRefreshMixin:
    """
    Auto-refresh proxy Mixin class

    Usage:
    1. Let client class inherit this Mixin
    2. Call init_proxy_pool(proxy_ip_pool) in client's __init__
    3. Call await _refresh_proxy_if_expired() before each request method call

    Requirements:
    - client class must have self.proxy attribute to store current proxy URL
    """

    _proxy_ip_pool: Optional["ProxyIpPool"] = None

    def init_proxy_pool(self, proxy_ip_pool: Optional["ProxyIpPool"]) -> None:
        """
        Initialize proxy pool reference
        Args:
            proxy_ip_pool: Proxy IP pool instance
        """
        self._proxy_ip_pool = proxy_ip_pool

    async def _refresh_proxy_if_expired(self) -> None:
        """
        Check if proxy has expired, automatically refresh if so
        Call this method before each request to ensure proxy is valid
        """
        if self._proxy_ip_pool is None:
            return

        if self._proxy_ip_pool.is_current_proxy_expired():
            utils.logger.info(
                f"[{self.__class__.__name__}._refresh_proxy_if_expired] Proxy expired, refreshing..."
            )
            new_proxy = await self._proxy_ip_pool.get_or_refresh_proxy()
            # Update httpx proxy URL
            if new_proxy.user and new_proxy.password:
                self.proxy = f"http://{new_proxy.user}:{new_proxy.password}@{new_proxy.ip}:{new_proxy.port}"
            else:
                self.proxy = f"http://{new_proxy.ip}:{new_proxy.port}"
            utils.logger.info(
                f"[{self.__class__.__name__}._refresh_proxy_if_expired] New proxy: {new_proxy.ip}:{new_proxy.port}"
            )


class ProxyFailoverMixin:
    """
    代理故障转移Mixin类
    
    提供带故障转移的请求能力:
    - 自动重试失败请求
    - 自动切换代理
    - 记录质量指标
    
    使用方法:
    1. 让客户端类继承此Mixin
    2. 调用 init_failover_manager() 初始化
    3. 使用 _request_with_failover() 发起请求
    """
    
    _failover_manager: Optional["ProxyFailoverManager"] = None
    _quality_evaluator: Optional["ProxyQualityEvaluator"] = None
    _current_proxy: Optional["IpInfoModel"] = None
    _max_retries: int = 3
    _retry_delay: float = 1.0
    
    def init_failover_manager(
        self,
        failover_manager: Optional["ProxyFailoverManager"] = None,
        quality_evaluator: Optional["ProxyQualityEvaluator"] = None,
        max_retries: int = 3,
        retry_delay: float = 1.0,
    ) -> None:
        """
        初始化故障转移管理器
        
        Args:
            failover_manager: 故障转移管理器
            quality_evaluator: 质量评估器
            max_retries: 最大重试次数
            retry_delay: 重试延迟（秒）
        """
        self._failover_manager = failover_manager
        self._quality_evaluator = quality_evaluator
        self._max_retries = max_retries
        self._retry_delay = retry_delay
    
    async def _get_proxy_with_failover(
        self,
        failed_proxy_id: Optional[str] = None,
    ) -> Optional["IpInfoModel"]:
        """
        获取代理（带故障转移）
        
        Args:
            failed_proxy_id: 上次失败的代理ID
            
        Returns:
            代理信息
        """
        if not self._failover_manager:
            return None
        
        proxy = await self._failover_manager.get_proxy(failed_proxy_id=failed_proxy_id)
        if proxy:
            self._current_proxy = proxy
            # 更新 self.proxy 属性
            self.proxy = proxy.to_url()
        
        return proxy
    
    async def _request_with_failover(
        self,
        request_func: Callable[..., Coroutine[Any, Any, T]],
        *args,
        **kwargs,
    ) -> T:
        """
        带故障转移的请求
        
        自动处理:
        - 代理过期刷新
        - 请求失败重试
        - 代理自动切换
        - 质量指标记录
        
        Args:
            request_func: 请求函数
            *args, **kwargs: 请求函数参数
            
        Returns:
            请求函数返回值
            
        Raises:
            Exception: 所有重试失败后抛出最后的异常
        """
        if not self._failover_manager:
            # 没有故障转移管理器，直接执行
            return await request_func(*args, **kwargs)
        
        last_exception = None
        failed_proxy_id = None
        
        for attempt in range(self._max_retries + 1):
            # 获取代理
            proxy = await self._get_proxy_with_failover(failed_proxy_id=failed_proxy_id)
            if not proxy:
                raise RuntimeError("No available proxies")
            
            start_time = time.time()
            
            try:
                # 执行请求
                result = await request_func(*args, **kwargs)
                
                # 记录成功
                response_time = (time.time() - start_time) * 1000
                self._failover_manager.report_success(proxy.proxy_id, response_time)
                
                if self._quality_evaluator:
                    await self._quality_evaluator.record_success(
                        proxy.proxy_id, response_time
                    )
                
                return result
                
            except Exception as e:
                last_exception = e
                failed_proxy_id = proxy.proxy_id
                
                # 记录失败
                self._failover_manager.report_failure(proxy.proxy_id)
                
                is_timeout = "timeout" in str(e).lower()
                if self._quality_evaluator:
                    await self._quality_evaluator.record_failure(
                        proxy.proxy_id,
                        is_timeout=is_timeout,
                        error_type=type(e).__name__,
                    )
                
                utils.logger.warning(
                    f"[{self.__class__.__name__}._request_with_failover] "
                    f"Request failed with proxy {proxy.ip}:{proxy.port}, "
                    f"attempt {attempt + 1}/{self._max_retries + 1}: {e}"
                )
                
                # 如果还有重试机会，等待后重试
                if attempt < self._max_retries:
                    await asyncio.sleep(self._retry_delay)
        
        # 所有重试都失败
        raise last_exception
    
    async def _report_proxy_result(
        self,
        success: bool,
        response_time_ms: float = 0,
        is_timeout: bool = False,
        error_type: Optional[str] = None,
    ) -> None:
        """
        报告代理请求结果（供外部调用）
        
        Args:
            success: 是否成功
            response_time_ms: 响应时间
            is_timeout: 是否超时
            error_type: 错误类型
        """
        if not self._current_proxy:
            return
        
        proxy_id = self._current_proxy.proxy_id
        
        if self._failover_manager:
            if success:
                self._failover_manager.report_success(proxy_id, response_time_ms)
            else:
                self._failover_manager.report_failure(proxy_id)
        
        if self._quality_evaluator:
            if success:
                await self._quality_evaluator.record_success(proxy_id, response_time_ms)
            else:
                await self._quality_evaluator.record_failure(
                    proxy_id,
                    is_timeout=is_timeout,
                    error_type=error_type,
                )


class EnhancedProxyMixin(ProxyRefreshMixin, ProxyFailoverMixin):
    """
    增强代理Mixin类
    
    组合了自动刷新和故障转移功能:
    - 支持传统的ProxyIpPool模式
    - 支持新的FailoverManager模式
    - 两种模式可以共存
    
    使用建议:
    - 简单场景使用 init_proxy_pool()
    - 需要高可用时使用 init_failover_manager()
    """
    
    async def _ensure_valid_proxy(self) -> None:
        """
        确保代理有效
        
        优先使用故障转移管理器，其次使用代理池
        """
        # 优先使用故障转移管理器
        if self._failover_manager:
            proxy = await self._get_proxy_with_failover()
            if proxy:
                return
        
        # 回退到传统代理池
        await self._refresh_proxy_if_expired()
